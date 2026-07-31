import re
from collections.abc import Sequence
from typing import (
    TYPE_CHECKING,
    Any,
)

import asyncpg
import msgspec

from .exceptions import SFAException
from .models import Row

if TYPE_CHECKING:
    from .database import Database

__all__ = ["RecordNotFoundError", "Repository", "RepositoryError"]


class RepositoryError(SFAException):
    """Base exception for repository-layer errors."""


class RecordNotFoundError(RepositoryError):
    """Raised when a single-record lookup finds nothing."""


PASCAL_TO_SNAKE = re.compile(r"(?<!^)(?=[A-Z])")


def to_table_name(cls: type[Row]) -> str:
    """Convert a Row class name to a table name."""
    return PASCAL_TO_SNAKE.sub("_", cls.__name__.removesuffix("Row")).lower()


class Repository[R: Row]:
    """
    Generic CRUD repository for a msgspec Struct mapped 1:1 to a table.

    Subclass and set the class vars:

        class UserRepository(BaseRepository[UserRow]):
            table = "users"
            model = UserRow
            pk = "id"
    """

    def __init__(self, database: "Database", *, row_cls: type[R]) -> None:
        self.database = database
        self.row_cls = row_cls
        self.table = to_table_name(row_cls)

        self._fields = [f.name for f in msgspec.structs.fields(self.row_cls)]
        self.primary_key = "id" if "id" in self._fields else "snowflake"

        self._non_pk_fields = [f for f in self._fields if f != self.primary_key]

    # -- conversion helpers --------------------------------------------

    def from_record(self, record: asyncpg.Record | None) -> R | None:
        if record is None:
            return None
        return msgspec.convert(dict(record), type=self.row_cls)

    def from_records(self, records: Sequence[asyncpg.Record]) -> list[R]:
        return [msgspec.convert(dict(r), type=self.row_cls) for r in records]

    # -- reads -----------------------------------------------------------

    async def get_by_pk(self, primary_key: Any) -> R | None:
        query = f"SELECT * FROM {self.table} WHERE {self.primary_key} = $1"
        record = await self.database.fetchrow(query, primary_key)
        return self.from_record(record)

    async def get_by_pk_or_raise(self, primary_key: Any) -> R:
        result = await self.get_by_pk(primary_key)

        if result is None:
            raise RecordNotFoundError(f"{self.table}.{self.primary_key}={primary_key!r} not found")

        return result

    async def list_all(self, *, limit: int = 100, offset: int = 0) -> list[R]:
        query = f"SELECT * FROM {self.table} ORDER BY {self.primary_key} LIMIT $1 OFFSET $2"
        records = await self.database.fetch(query, limit, offset)
        return self.from_records(records)

    async def find_by(self, **filters: Any) -> list[R]:
        """Simple equality-filter lookup, e.g. repo.find_by(user_id=5, active=True)."""
        if not filters:
            raise ValueError("find_by() called with no filters")

        columns = list(filters.keys())
        where_clause = " AND ".join(f"{col} = ${i}" for i, col in enumerate(columns, start=1))
        query = f"SELECT * FROM {self.table} WHERE {where_clause}"
        records = await self.database.fetch(query, *filters.values())

        return self.from_records(records)

    async def count(self, **filters: Any) -> int:
        if not filters:
            query = f"SELECT COUNT(*) FROM {self.table}"
            return await self.database.fetchval(query)

        columns = list(filters.keys())
        where_clause = " AND ".join(f"{col} = ${i}" for i, col in enumerate(columns, start=1))
        query = f"SELECT COUNT(*) FROM {self.table} WHERE {where_clause}"

        return await self.database.fetchval(query, *filters.values())

    # -- writes ----------------------------------------------------------

    async def insert(self, obj: R) -> R | None:
        columns = self._fields
        placeholders = ", ".join(f"${i}" for i in range(1, len(columns) + 1))
        query = f"INSERT INTO {self.table} ({', '.join(columns)}) VALUES ({placeholders}) RETURNING *"

        record = await self.database.fetchrow(query, *msgspec.structs.astuple(obj))
        return self.from_record(record)

    async def update(self, primary_key: Any, **changes: Any) -> R | None:
        """Partial update - only touches the fields you pass."""
        if not changes:
            raise RepositoryError("update() called with no fields to change")

        set_clause = ", ".join(f"{col} = ${i}" for i, col in enumerate(changes.keys(), start=2))
        query = f"UPDATE {self.table} SET {set_clause} WHERE {self.primary_key} = $1 RETURNING *"

        record = await self.database.fetchrow(query, primary_key, *changes.values())
        return self.from_record(record)

    async def delete(self, primary_key: Any) -> bool:
        query = f"DELETE FROM {self.table} WHERE {self.primary_key} = $1"
        result = await self.database.execute(query, primary_key)

        # asyncpg execute() returns e.g. "DELETE 1"
        return result.split()[-1] != "0"

    # -- bulk ops -----------------------------------------------------

    async def bulk_insert(self, objs: Sequence[R]) -> None:
        """Fastest path for large batches - uses COPY, no RETURNING support."""
        if not objs:
            return

        records = [msgspec.structs.astuple(o) for o in objs]
        await self.database.copy_records_to_table(self.table, records, columns=self._fields)
