import datetime

from msgspec import field

from .base import Row

__all__ = [
    "GameRow",
]


class GameRow(Row, dict=True, kw_only=True):
    """Match results with referees, streamers, and score reporting."""

    id: int
    season_id: int

    home_team_id: int | None = field(default=None)
    away_team_id: int | None = field(default=None)

    home_score: int | None = field(default=None)
    away_score: int | None = field(default=None)

    is_forfeit: bool
    is_double_forfeit: bool
    forfeit_by_home: bool | None = field(default=None)
    forfeit_by_away: bool | None = field(default=None)

    stage: int
    division: int | None = field(default=None)
    subdivision: int | None = field(default=None)
    week: int | None = field(default=None)

    scheduled_for: datetime.datetime
    thread_snowflake: int
    referee_snowflakes: list[int] = field(default_factory=list)
    streamers: dict[int, str] = field(default_factory=dict)

    reporter_snowflake: int
    reported_at: datetime.datetime

    approver_snowflake: int | None = field(default=None)
    approved_at: datetime.datetime | None = field(default=None)

    version: int

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
