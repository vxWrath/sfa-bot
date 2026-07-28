import datetime

from structhook import field

from .base import DatabaseModel

__all__ = [
    "TeamSeasonStage",
]


class TeamSeasonStage(DatabaseModel):
    """Per-stage snapshot: division, playoff round, or championship placement.

    One row per team per season per stage (1-9).
    Stages 1-5 are group stages, 6-9 are playoff rounds.
    """

    id: int
    season_id: int
    team_id: int
    stage: int

    division: int | None = field(default=None)
    subdivision: str | None = field(default=None)
    gsp: int | None = field(default=None)

    is_play_in: bool | None = field(default=None)
    is_auto_qualified: bool | None = field(default=None)
    is_champion: bool = field(default=False)

    is_finished: bool | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
