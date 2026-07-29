from typing import TYPE_CHECKING

from ..models import SeasonProfile

if TYPE_CHECKING:
    from ..database import Database

__all__ = [
    "SeasonService",
]


class SeasonService:
    """Multi-table queries for seasons."""

    def __init__(self, database: "Database") -> None:
        self.database = database

        self.seasons = database.get_repository("season")
        self.awards = database.get_repository("award")
        self.games = database.get_repository("game")
        self.player_stats = database.get_repository("player_stat")
        self.team_season_stages = database.get_repository("team_season_stage")

    async def get_profile(self, season_id: int) -> SeasonProfile:
        """Fetch a season and all related records."""
        season = await self.seasons.get_by_pk_or_raise(season_id)

        awards = await self.awards.find_by(season_id=season_id)
        games = await self.games.find_by(season_id=season_id)
        player_stats = await self.player_stats.find_by(season_id=season_id)
        team_stages = await self.team_season_stages.find_by(season_id=season_id)

        return SeasonProfile(
            season=season,
            awards=awards,
            games=games,
            player_stats=player_stats,
            team_stages=team_stages,
        )
