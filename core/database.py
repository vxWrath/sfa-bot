import asyncio
import datetime
import struct
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import Any, Literal, TypedDict, Unpack

import asyncpg
import orjson

from .env import get_env
from .exceptions import SFAException
from .logging import get_logger
from .models import Row
from .repository import Repository

logger = get_logger("database")


class DatabaseError(SFAException):
    """Raised when a database error occurs."""


class DatabaseNotConnected(SFAException):
    """Raised when a database operation is attempted before connecting to the database."""


IsolationLevel = Literal[
    "read_committed",
    "repeatable_read",
    "serializable",
    "read_uncommitted",
]


# Dict-like encoders/decoders
def _dumps(obj: Any) -> str:
    return orjson.dumps(obj).decode("utf-8")


def _loads(obj: Any) -> Any:
    if obj == '"{}"':
        return {}
    return orjson.loads(obj)


# Datetime handling for timestamptz columns (PostgreSQL sends these as ISO strings)
def _datetime_encoder(dt: str | datetime.datetime) -> str:
    if isinstance(dt, datetime.datetime):
        return dt.isoformat()
    return dt


def _datetime_decoder(dt_str: str) -> datetime.datetime:
    fixed = dt_str.replace("T", " ").replace("Z", "+00:00")
    return datetime.datetime.fromisoformat(fixed)


# Postgres binary format: 8-byte big-endian, microseconds since 2000-01-01 UTC.
_POSTGRES_EPOCH = datetime.datetime(2000, 1, 1, tzinfo=datetime.UTC)


def _datetime_binary_encoder(dt: datetime.datetime) -> bytes:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.UTC)
    delta = dt - _POSTGRES_EPOCH
    microseconds = int(delta.total_seconds() * 1_000_000)
    return struct.pack(">q", microseconds)


def _datetime_binary_decoder(data: bytes) -> datetime.datetime:
    (microseconds,) = struct.unpack(">q", data)
    return _POSTGRES_EPOCH + datetime.timedelta(microseconds=microseconds)


async def postgres_init(connection: asyncpg.Connection) -> None:
    await connection.set_type_codec(
        "jsonb",
        encoder=_dumps,
        decoder=_loads,
        schema="pg_catalog",
        format="text",
    )
    await connection.set_type_codec(
        "timestamptz",
        encoder=_datetime_encoder,
        decoder=_datetime_decoder,
        schema="pg_catalog",
        format="text",
    )
    await connection.set_type_codec(
        "timestamptz",
        encoder=_datetime_binary_encoder,
        decoder=_datetime_binary_decoder,
        schema="pg_catalog",
        format="binary",
    )


class DatabaseOptions(TypedDict, total=False):
    min_size: int
    max_size: int
    max_inactive_connection_lifetime: float
    command_timeout: float
    statement_cache_size: int
    max_queries: int
    init: Any
    connect_retries: int
    connect_retry_delay: float


class Database:
    """Database connection manager."""

    def __init__(self, **kwargs: Unpack[DatabaseOptions]) -> None:
        self._min_size = kwargs.get("min_size", 5)
        self._max_size = kwargs.get("max_size", 20)
        self._max_inactive_connection_lifetime = kwargs.get("max_inactive_connection_lifetime", 300.0)
        self._command_timeout = kwargs.get("command_timeout", 30.0)
        self._statement_cache_size = kwargs.get("statement_cache_size", 1024)
        self._max_queries = kwargs.get("max_queries", 50_000)
        self._init = kwargs.get("init", postgres_init)
        self._connect_retries = kwargs.get("connect_retries", 5)
        self._connect_retry_delay = kwargs.get("connect_retry_delay", 1.0)

        self._pool: asyncpg.Pool | None = None
        self._connection_lock = asyncio.Lock()
        self._repositories = {row: Repository(self, row_cls=row) for row in Row.__subclasses__()}

    async def connect(self) -> None:
        """Connect to the database."""

        if self._pool is not None:
            return

        async with self._connection_lock:
            if self._pool is not None:
                return

            last_exception: Exception | None = None

            for attempt in range(1, self._connect_retries + 1):
                try:
                    self._pool = await asyncpg.create_pool(
                        dsn=get_env("DATABASE_URL"),
                        min_size=self._min_size,
                        max_size=self._max_size,
                        max_inactive_connection_lifetime=self._max_inactive_connection_lifetime,
                        command_timeout=self._command_timeout,
                        statement_cache_size=self._statement_cache_size,
                        max_queries=self._max_queries,
                        init=self._init,
                    )

                    logger.info("Postgres pool created (min=%d, max=%d)", self._min_size, self._max_size)
                    return
                except (
                    OSError,
                    asyncpg.CannotConnectNowError,
                    asyncpg.ConnectionDoesNotExistError,
                    asyncpg.TooManyConnectionsError,
                ) as e:
                    last_exception = e
                    logger.warning(
                        "Postgres connection attempt %d/%d failed: %s",
                        attempt,
                        self._connect_retries,
                        e,
                    )

                    if attempt < self._connect_retries:
                        await asyncio.sleep(self._connect_retry_delay * attempt)

        raise DatabaseError(f"Failed to connect to Postgres after {self._connect_retries} attempts") from last_exception

    async def close(self) -> None:
        """Gracefully close the database connection."""

        if self._pool is None:
            return

        await self._pool.close()
        self._pool = None

        logger.info("Postgres pool closed")

    @property
    def pool(self) -> asyncpg.Pool:
        """Get the underlying asyncpg.Pool instance."""

        if self._pool is None:
            raise DatabaseNotConnected("Database.connect() must be called before use")

        return self._pool

    # Query methods

    async def fetch(self, query: str, *args: Any, timeout: float | None = None) -> list[asyncpg.Record]:
        """Fetch a query result."""

        async with self.pool.acquire() as c:
            return await c.fetch(query, *args, timeout=timeout)

    async def fetchrow(self, query: str, *args: Any, timeout: float | None = None) -> asyncpg.Record | None:
        """Fetch a single row from a query."""

        async with self.pool.acquire() as c:
            return await c.fetchrow(query, *args, timeout=timeout)

    async def fetchval(self, query: str, *args: Any, column: int = 0, timeout: float | None = None) -> Any:
        """Fetch a single value from a query."""

        async with self.pool.acquire() as c:
            return await c.fetchval(query, *args, column=column, timeout=timeout)

    async def execute(self, query: str, *args: Any, timeout: float | None = None) -> str:
        """Execute a query."""

        async with self.pool.acquire() as c:
            return await c.execute(query, *args, timeout=timeout)

    async def executemany(self, query: str, args: Sequence[Sequence[Any]], timeout: float | None = None) -> None:
        """Execute a query with multiple arguments."""

        async with self.pool.acquire() as c:
            await c.executemany(query, args, timeout=timeout)

    async def copy_records_to_table(
        self,
        table: str,
        records: Sequence[Sequence[Any]],
        columns: Sequence[str],
        *,
        schema_name: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """"""

        async with self.pool.acquire() as c:
            return await c.copy_records_to_table(
                table,
                records=records,
                columns=columns,
                schema_name=schema_name,
                timeout=timeout,
            )

    @asynccontextmanager
    async def transaction(
        self,
        *,
        isolation: IsolationLevel = "read_committed",
        readonly: bool = False,
        deferrable: bool = False,
    ) -> AsyncGenerator[asyncpg.Connection]:
        """Acquire a dedicated connection and run a transaction."""

        async with self.pool.acquire() as c:
            async with c.transaction(isolation=isolation, readonly=readonly, deferrable=deferrable):
                yield c  # type: ignore

    def get_repository[R: Row](self, row: type[R]) -> Repository[R]:
        """Get a repository for a table."""
        return self._repositories[row]  # type: ignore
