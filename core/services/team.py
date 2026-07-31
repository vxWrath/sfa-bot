from typing import TYPE_CHECKING

from ..models import (
    AwardAssignmentRow,
    ContractRow,
    GameRow,
    PlayerStatRow,
    TeamOwnerHistoryRow,
    TeamProfile,
    TeamRow,
    TeamSeasonStageRow,
)

if TYPE_CHECKING:
    from ..database import Database

__all__ = [
    "TeamService",
]


class TeamService:
    """Multi-table queries for teams."""

    def __init__(self, database: "Database") -> None:
        self.database = database

        self.teams = database.get_repository(TeamRow)
        self.award_assignments = database.get_repository(AwardAssignmentRow)
        self.contracts = database.get_repository(ContractRow)
        self.games = database.get_repository(GameRow)
        self.player_stats = database.get_repository(PlayerStatRow)
        self.team_owner_history = database.get_repository(TeamOwnerHistoryRow)
        self.team_season_stages = database.get_repository(TeamSeasonStageRow)

    async def get_profile(self, team_id: int) -> TeamProfile:
        """Fetch a team and all related records."""
        team = await self.teams.get_by_pk_or_raise(team_id)

        award_assignments = await self.award_assignments.find_by(team_id=team_id)
        contracts = await self.contracts.find_by(team_id=team_id)
        home_games = await self.games.find_by(home_team_id=team_id)
        away_games = await self.games.find_by(away_team_id=team_id)
        player_stats = await self.player_stats.find_by(team_id=team_id)
        owner_history = await self.team_owner_history.find_by(team_id=team_id)
        season_stages = await self.team_season_stages.find_by(team_id=team_id)

        return TeamProfile(
            team=team,
            award_assignments=award_assignments,
            contracts=contracts,
            home_games=home_games,
            away_games=away_games,
            player_stats=player_stats,
            owner_history=owner_history,
            season_stages=season_stages,
        )
