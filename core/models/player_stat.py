import datetime
from typing import Any

from msgspec import Struct, field

__all__ = [
    "PlayerStatRow",
]


class PlayerStatRow(Struct, dict=True, kw_only=True):
    """Per-player per-game position stats stored as JSONB."""

    id: int

    game_id: int
    season_id: int | None = field(default=None)
    team_id: int

    roblox_id: int
    player_snowflake: int | None = field(default=None)

    quarterback: dict[str, Any] | None = field(default=None)
    rushing: dict[str, Any] | None = field(default=None)
    receiver: dict[str, Any] | None = field(default=None)
    corner: dict[str, Any] | None = field(default=None)
    defender: dict[str, Any] | None = field(default=None)
    kicker: dict[str, Any] | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
