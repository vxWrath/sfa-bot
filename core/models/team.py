import datetime

from structhook import DotDict, field

from .award_assignment import AwardAssignment
from .base import DatabaseModel
from .contract import Contract
from .game import Game
from .player_stat import PlayerStat
from .team_owner_history import TeamOwnerHistory
from .team_season_stage import TeamSeasonStage

__all__ = [
    "Team",
]


class Team(DatabaseModel):
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

    award_assignments: DotDict[int, AwardAssignment] = field(default_factory=DotDict, exclude=True)
    contracts: DotDict[int, Contract] = field(default_factory=DotDict, exclude=True)
    home_games: DotDict[int, Game] = field(default_factory=DotDict, exclude=True)
    away_games: DotDict[int, Game] = field(default_factory=DotDict, exclude=True)
    player_stats: DotDict[int, PlayerStat] = field(default_factory=DotDict, exclude=True)
    owner_history: DotDict[int, TeamOwnerHistory] = field(default_factory=DotDict, exclude=True)
    season_stages: DotDict[int, TeamSeasonStage] = field(default_factory=DotDict, exclude=True)
