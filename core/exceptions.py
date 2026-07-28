from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models.base import DatabaseModel


class SFAException(Exception):
    """Base class for SFA exceptions."""


class DatabaseNotBound(SFAException):
    """Raised when a database operation is attempted on a model that is not bound to a database."""

    def __init__(self, obj: "DatabaseModel") -> None:
        super().__init__(f"Database not bound to this object of type {type(obj).__name__}.")
