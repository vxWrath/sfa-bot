from msgspec import Struct

from ..award_assignment import AwardAssignmentRow
from ..contract import ContractRow
from ..game import GameRow
from ..player_stat import PlayerStatRow
from ..team import TeamRow
from ..team_owner_history import TeamOwnerHistoryRow
from ..team_season_stage import TeamSeasonStageRow

__all__ = [
    "TeamProfile",
]


class TeamProfile(Struct, dict=True, kw_only=True):
    """Aggregated team view row + all related records."""

    team: TeamRow
    award_assignments: list[AwardAssignmentRow]
    contracts: list[ContractRow]
    home_games: list[GameRow]
    away_games: list[GameRow]
    player_stats: list[PlayerStatRow]
    owner_history: list[TeamOwnerHistoryRow]
    season_stages: list[TeamSeasonStageRow]
