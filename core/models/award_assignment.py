import datetime

from msgspec import Struct, field

__all__ = [
    "AwardAssignmentRow",
]


class AwardAssignmentRow(Struct, dict=True, kw_only=True):
    """Awards granted to players or teams."""

    id: int
    award_id: int
    player_snowflake: int | None = field(default=None)
    team_id: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
