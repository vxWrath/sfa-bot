from msgspec import Struct

from ..award import AwardRow
from ..award_assignment import AwardAssignmentRow

__all__ = [
    "AwardProfile",
]


class AwardProfile(Struct, dict=True, kw_only=True):
    """Aggregated award view row + all related records."""

    award: AwardRow
    assignments: list[AwardAssignmentRow]
