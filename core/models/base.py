from functools import cache
from typing import TYPE_CHECKING, Any, Self

from structhook import HookStruct

from ..exceptions import DatabaseNotBound

if TYPE_CHECKING:
    type Database = Any  # TODO: import from ..database

__all__ = ["DatabaseModel"]


class DatabaseModel(HookStruct):
    """Base class for database models."""

    @property
    def database(self) -> "Database":
        db = self.__dict__.get("_database")

        if not db:
            raise DatabaseNotBound(self)

        return db

    def bind(self, db: "Database") -> Self:
        """Bind a database instance to this table model."""
        self["_database"] = db
        return self

    @classmethod
    @cache
    def required_cols(cls) -> tuple[str, ...]:
        """Return a set of required field names for this model."""
        return tuple(key for key, field in cls.__fields__.items() if field.extra and field.extra.get("required", False))

    @classmethod
    @cache
    def cols(cls) -> tuple[str, ...]:
        """Return a set of all field names for this model."""
        return tuple(key for key, field in cls.__fields__.items() if not field.exclude)

    @classmethod
    @cache
    def insert_cols(cls) -> tuple[str, ...]:
        """Return a set of field names that should be included in insert operations for this model."""
        return tuple(
            key for key, field in cls.__fields__.items() if not field.exclude and key not in {"id", "snowflake"}
        )
