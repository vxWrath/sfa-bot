import datetime

from msgspec import field

from .base import Row

__all__ = [
    "AwardRow",
]


class AwardRow(Row, dict=True, kw_only=True):
    """Custom awards - can be seasonal or HOF-style (no season)."""

    id: int
    season_id: int | None = field(default=None)
    name: str
    category: str
    description: str
    role_snowflake: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
