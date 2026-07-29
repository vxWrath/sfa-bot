from msgspec import Struct

from ..award_assignment import AwardAssignmentRow
from ..contract import ContractRow
from ..game import GameRow
from ..player import PlayerRow
from ..player_sanction import PlayerSanctionRow
from ..player_stat import PlayerStatRow
from ..team_owner_history import TeamOwnerHistoryRow

__all__ = [
    "PlayerProfile",
]


class PlayerProfile(Struct, dict=True, kw_only=True):
    """Aggregated player view row + all related records."""

    player: PlayerRow
    contracts: list[ContractRow]
    sanctions: list[PlayerSanctionRow]
    moderated_sanctions: list[PlayerSanctionRow]
    team_owner_history: list[TeamOwnerHistoryRow]
    award_assignments: list[AwardAssignmentRow]
    reported_games: list[GameRow]
    approved_games: list[GameRow]
    stats: list[PlayerStatRow]
