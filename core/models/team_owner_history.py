import datetime

from structhook import field

from .base import DatabaseModel


class TeamOwnerHistory(DatabaseModel):
    """Ownership change log - tracks who owned a team and when."""

    id: int

    player_snowflake: int
    team_id: int

    appointed_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    unappointed_at: datetime.datetime | None = field(default=None)
    is_active: bool = True

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
