from msgspec import Struct

__all__ = [
    "Row",
]


class Row(Struct, dict=True, kw_only=True):
    """Base class for all database rows."""
