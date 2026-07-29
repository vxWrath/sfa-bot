from typing import TYPE_CHECKING

from ..models import AwardProfile, AwardRow

if TYPE_CHECKING:
    from ..database import Database

__all__ = [
    "AwardService",
]


class AwardService:
    """Multi-table queries for awards."""

    def __init__(self, database: "Database") -> None:
        self.database = database

        self.awards = database.get_repository("award")
        self.award_assignments = database.get_repository("award_assignment")

    async def get_profile(self, award_id: int) -> AwardProfile:
        """Fetch an award and all related records."""
        award = await self.awards.get_by_pk_or_raise(award_id)
        assignments = await self.award_assignments.find_by(award_id=award_id)

        return AwardProfile(
            award=award,
            assignments=assignments,
        )
