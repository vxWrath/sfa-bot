import datetime

from msgspec import Struct, field

__all__ = [
    "PlayerRow",
]


class PlayerRow(Struct, dict=True, kw_only=True):
    """Discord user linked to a Roblox account."""

    snowflake: int
    roblox_id: int | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
