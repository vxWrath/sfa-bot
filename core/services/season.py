from typing import TYPE_CHECKING

from ..models import (
    AwardRow,
    GameRow,
    PlayerStatRow,
    SeasonProfile,
    SeasonRow,
    TeamSeasonStageRow,
)

if TYPE_CHECKING:
    from ..database import Database

__all__ = [
    "SeasonService",
]


class SeasonService:
    """Multi-table queries for seasons."""

    def __init__(self, database: "Database") -> None:
        self.database = database

        self.seasons = database.get_repository(SeasonRow)
        self.awards = database.get_repository(AwardRow)
        self.games = database.get_repository(GameRow)
        self.player_stats = database.get_repository(PlayerStatRow)
        self.team_season_stages = database.get_repository(TeamSeasonStageRow)

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
