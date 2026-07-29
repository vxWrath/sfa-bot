from typing import TYPE_CHECKING

from ..models import GameProfile, GameRow

if TYPE_CHECKING:
    from ..database import Database

__all__ = [
    "GameService",
]


class GameService:
    """Multi-table queries for games."""

    def __init__(self, database: "Database") -> None:
        self.database = database

        self.games = database.get_repository("game")
        self.player_stats = database.get_repository("player_stat")

    async def get_profile(self, game_id: int) -> GameProfile:
        """Fetch a game and all related records."""
        game = await self.games.get_by_pk_or_raise(game_id)
        player_stats = await self.player_stats.find_by(game_id=game_id)

        return GameProfile(
            game=game,
            player_stats=player_stats,
        )