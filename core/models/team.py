import datetime

from msgspec import field

from .base import Row

__all__ = [
    "TeamRow",
]


class TeamRow(Row, dict=True, kw_only=True):
    """Franchise with division tracking."""

    id: int
    role_snowflake: int | None
    role_name: str

    division: int | None = field(default=None)
    subdivision: int | None = field(default=None)
    gsp: int | None = field(default=None)

    is_active: bool

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
