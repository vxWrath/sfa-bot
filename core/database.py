import asyncio
import datetime
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from typing import Any, Literal, NotRequired, TypedDict, Unpack, overload

import asyncpg
import orjson

from .env import get_env
from .exceptions import SFAException
from .logging import get_logger
from .models import (
    AwardAssignmentRow,
    AwardRow,
    CoachRow,
    ContractRow,
    GameRow,
    PlayerRow,
    PlayerSanctionRow,
    PlayerStatRow,
    SeasonRow,
    TeamOwnerHistoryRow,
    TeamRow,
    TeamSeasonStageRow,
)
from .repository import Repository

logger = get_logger("database")


class DatabaseError(SFAException):
    """Raised when a database error occurs."""


class DatabaseNotConnected(SFAException):
    """Raised when a database operation is attempted before connecting to the database."""


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


class DatabaseOptions(TypedDict):
    min_size: NotRequired[int]
    max_size: NotRequired[int]
    max_inactive_connection_lifetime: NotRequired[float]
    command_timeout: NotRequired[float]
    statement_cache_size: NotRequired[int]
    max_queries: NotRequired[int]
    init: NotRequired[Any]
    connect_retries: NotRequired[int]
    connect_retry_delay: NotRequired[float]


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

        # fmt: off
        self._repositories: dict[str, Repository[Any]] = {
            "award_assignment": Repository(
                self, table="award_assignments", model_cls=AwardAssignmentRow, primary_key="id"
            ),
            "award": Repository(
                self, table="awards", model_cls=AwardRow, primary_key="id"
            ),
            "coach": Repository(
                self, table="coaches", model_cls=CoachRow, primary_key="id"
            ),
            "contract": Repository(
                self, table="contracts", model_cls=ContractRow, primary_key="id"
            ),
            "game": Repository(
                self, table="games", model_cls=GameRow, primary_key="id"
            ),
            "player_sanction": Repository(
                self, table="player_sanctions", model_cls=PlayerSanctionRow, primary_key="id"
            ),
            "player_stat": Repository(
                self, table="player_stats", model_cls=PlayerStatRow, primary_key="id"
            ),
            "player": Repository(
                self, table="players", model_cls=PlayerRow, primary_key="snowflake"
            ),
            "season": Repository(
                self, table="seasons", model_cls=SeasonRow, primary_key="id"
            ),
            "team_owner_history": Repository(
                self, table="team_owner_histories", model_cls=TeamOwnerHistoryRow, primary_key="id"
            ),
            "team_season_stage": Repository(
                self, table="team_season_stages", model_cls=TeamSeasonStageRow, primary_key="id"
            ),
            "team": Repository(
                self, table="teams", model_cls=TeamRow, primary_key="id"
            ),
        }
        # fmt: on

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
                except (OSError, asyncpg.PostgresError) as e:
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

    async def terminate(self) -> None:
        """Terminate the database connection. Does not wait for queries to finish."""

        if self._pool is None:
            return

        self._pool.terminate()
        self._pool = None

        logger.info("Postgres pool terminated")

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
                schema=schema_name,
                timeout=timeout,
            )

    @asynccontextmanager
    async def transaction(
        self,
        *,
        isolation: str = "read_committed",
        readonly: bool = False,
        deferrable: bool = False,
    ) -> AsyncGenerator[asyncpg.Connection]:
        """Acquire a dedicated connection and run a transaction."""

        async with self.pool.acquire() as c:
            async with c.transaction(isolation=isolation, readonly=readonly, deferrable=deferrable):
                yield c  # type: ignore

    @overload
    def get_repository(self, table: Literal["award_assignment"]) -> Repository[AwardAssignmentRow]: ...
    @overload
    def get_repository(self, table: Literal["award"]) -> Repository[AwardRow]: ...
    @overload
    def get_repository(self, table: Literal["coach"]) -> Repository[CoachRow]: ...
    @overload
    def get_repository(self, table: Literal["contract"]) -> Repository[ContractRow]: ...
    @overload
    def get_repository(self, table: Literal["game"]) -> Repository[GameRow]: ...
    @overload
    def get_repository(self, table: Literal["player_sanction"]) -> Repository[PlayerSanctionRow]: ...
    @overload
    def get_repository(self, table: Literal["player_stat"]) -> Repository[PlayerStatRow]: ...
    @overload
    def get_repository(self, table: Literal["player"]) -> Repository[PlayerRow]: ...
    @overload
    def get_repository(self, table: Literal["season"]) -> Repository[SeasonRow]: ...
    @overload
    def get_repository(self, table: Literal["team_owner_history"]) -> Repository[TeamOwnerHistoryRow]: ...
    @overload
    def get_repository(self, table: Literal["team_season_stage"]) -> Repository[TeamSeasonStageRow]: ...
    @overload
    def get_repository(self, table: Literal["team"]) -> Repository[TeamRow]: ...

    def get_repository(self, table: str) -> Repository[Any]:
        """Get a repository for a table."""

        if table not in self._repositories:
            raise DatabaseError(f"No repository for table '{table}'")

        return self._repositories[table]
