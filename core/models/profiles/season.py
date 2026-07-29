from msgspec import Struct

from ..award import AwardRow
from ..game import GameRow
from ..player_stat import PlayerStatRow
from ..season import SeasonRow
from ..team_season_stage import TeamSeasonStageRow

__all__ = [
    "SeasonProfile",
]


class SeasonProfile(Struct, dict=True, kw_only=True):
    """Aggregated season view row + all related records."""

    season: SeasonRow
    awards: list[AwardRow]
    games: list[GameRow]
    player_stats: list[PlayerStatRow]
    team_stages: list[TeamSeasonStageRow]
