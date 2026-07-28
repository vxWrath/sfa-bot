import datetime

from structhook import DotDict, field

from .base import DatabaseModel

__all__ = [
    "PlayerSanction",
]


class PlayerSanction(DatabaseModel):
    """Suspensions and team-owner blacklists.

    sanction_type enum: 0=suspension, 1=team owner blacklist
    """

    id: int
    player_snowflake: int

    sanction_type: int
    moderator_snowflake: int | None = field(default=None)

    sanctioned_until: datetime.datetime | None = field(default=None)
    sanctioned_at: datetime.datetime | None = field(default=None)
    justification: DotDict | None = field(default=None)
    banned_until: datetime.datetime | None = field(default=None)

    is_active: bool

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
