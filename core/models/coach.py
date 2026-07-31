import datetime

from msgspec import field

from .base import Row

__all__ = [
    "CoachRow",
]


class CoachRow(Row, dict=True, kw_only=True):
    """Person-based coaching staff."""

    id: int

    role_snowflake: int | None
    role_name: str
    acronym: str | None = field(default=None)
    sort_index: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
