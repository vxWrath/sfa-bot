from typing import TYPE_CHECKING

from ..models import (
    AwardAssignmentRow,
    ContractRow,
    GameRow,
    PlayerProfile,
    PlayerRow,
    PlayerSanctionRow,
    PlayerStatRow,
    TeamOwnerHistoryRow,
)

if TYPE_CHECKING:
    from ..database import Database

__all__ = [
    "PlayerService",
]


class PlayerService:
    """Multi-table queries for players."""

    def __init__(self, database: "Database") -> None:
        self.database = database

        self.players = database.get_repository(PlayerRow)
        self.contracts = database.get_repository(ContractRow)
        self.player_sanctions = database.get_repository(PlayerSanctionRow)
        self.team_owner_history = database.get_repository(TeamOwnerHistoryRow)
        self.award_assignments = database.get_repository(AwardAssignmentRow)
        self.games = database.get_repository(GameRow)
        self.player_stats = database.get_repository(PlayerStatRow)

    async def get_profile(self, snowflake: int) -> PlayerProfile:
        """Fetch a player and all related records."""
        player = await self.players.get_by_pk_or_raise(snowflake)

        contracts = await self.contracts.find_by(player_snowflake=snowflake)
        sanctions = await self.player_sanctions.find_by(player_snowflake=snowflake)
        moderated_sanctions = await self.player_sanctions.find_by(moderator_snowflake=snowflake)
        team_owner_history = await self.team_owner_history.find_by(player_snowflake=snowflake)
        award_assignments = await self.award_assignments.find_by(player_snowflake=snowflake)
        reported_games = await self.games.find_by(reporter_snowflake=snowflake)
        approved_games = await self.games.find_by(approver_snowflake=snowflake)
        stats = await self.player_stats.find_by(player_snowflake=snowflake)

        return PlayerProfile(
            player=player,
            contracts=contracts,
            sanctions=sanctions,
            moderated_sanctions=moderated_sanctions,
            team_owner_history=team_owner_history,
            award_assignments=award_assignments,
            reported_games=reported_games,
            approved_games=approved_games,
            stats=stats,
        )
