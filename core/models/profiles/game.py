from msgspec import Struct

from ..game import GameRow
from ..player_stat import PlayerStatRow

__all__ = [
    "GameProfile",
]


class GameProfile(Struct, dict=True, kw_only=True):
    """Aggregated game view row + all related records."""

    game: GameRow
    player_stats: list[PlayerStatRow]
