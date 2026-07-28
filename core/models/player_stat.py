import datetime

from structhook import DotDict, field

from .base import DatabaseModel

__all__ = [
    "PlayerStat",
]


class PlayerStat(DatabaseModel):
    """Per-player per-game position stats stored as JSONB."""

    id: int

    game_id: int
    season_id: int | None = field(default=None)
    team_id: int

    roblox_id: int
    player_snowflake: int | None = field(default=None)

    quarterback: DotDict | None = field(default=None)
    rushing: DotDict | None = field(default=None)
    receiver: DotDict | None = field(default=None)
    corner: DotDict | None = field(default=None)
    defender: DotDict | None = field(default=None)
    kicker: DotDict | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
