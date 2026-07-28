import datetime

from structhook import DotDict, field

from .award_assignment import AwardAssignment
from .base import DatabaseModel

__all__ = [
    "Award",
]


class Award(DatabaseModel):
    """Custom awards - can be seasonal or HOF-style (no season)."""

    id: int
    season_id: int | None = field(default=None)
    name: str
    category: str
    description: str
    role_snowflake: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))

    assignments: DotDict[int, AwardAssignment] = field(default_factory=DotDict, exclude=True)
