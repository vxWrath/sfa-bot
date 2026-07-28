import datetime

from structhook import field

from .base import DatabaseModel

__all__ = [
    "AwardAssignment",
]


class AwardAssignment(DatabaseModel):
    """Awards granted to players or teams."""

    id: int
    award_id: int
    player_snowflake: int | None = field(default=None)
    team_id: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
