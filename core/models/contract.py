import datetime

from structhook import DotDict, field

from .base import DatabaseModel

__all__ = [
    "Contract",
]


class Contract(DatabaseModel):
    """Active roster contract record.

    length_type enum: 0=games, 1=weeks, 2=months, 3=seasons
    """

    id: int
    player_snowflake: int
    team_id: int

    amount: float | None = field(default=None)
    notes: str
    length: int
    length_type: int

    started_at: datetime.datetime | None = field(default=None)
    expires_at: datetime.datetime | None = field(default=None)

    terminated_at: datetime.datetime | None = field(default=None)
    termination_justification: DotDict | None = field(default=None)

    is_active: bool
    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
