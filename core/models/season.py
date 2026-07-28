import datetime

from structhook import DotDict, field

from .award import Award
from .base import DatabaseModel
from .game import Game
from .player_stat import PlayerStat
from .team_season_stage import TeamSeasonStage

__all__ = [
    "Season",
]


class Season(DatabaseModel):
    """Season & stage tracking.

    current_stage enum:
      1=GROUP_1, 2=GROUP_2, 3=GROUP_3, 4=GROUP_4, 5=GROUP_5,
      6=PLAYOFFS_R1, 7=PLAYOFFS_QF, 8=PLAYOFFS_SF, 9=PLAYOFFS_FINAL
    """

    id: int
    season_number: int
    current_stage: int = field(default=1)

    is_playoffs: bool = field(default=False)

    is_active: bool = field(default=True)
    version: int = field(default=1)

    started_at: datetime.datetime | None = field(default=None)
    ended_at: datetime.datetime | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

    awards: DotDict[int, Award] = field(default_factory=DotDict, exclude=True)
    games: DotDict[int, Game] = field(default_factory=DotDict, exclude=True)
    player_stats: DotDict[int, PlayerStat] = field(default_factory=DotDict, exclude=True)
    team_stages: DotDict[int, TeamSeasonStage] = field(default_factory=DotDict, exclude=True)
