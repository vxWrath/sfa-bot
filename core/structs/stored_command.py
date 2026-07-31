from typing import TYPE_CHECKING

import discord
from msgspec import Struct, field

if TYPE_CHECKING:
    from sfa_bot.services.bot import SFABot
    from sfa_bot.services.cooldowns import CooldownManager

__all__ = ["StoredCommand"]


class StoredCommand(Struct):
    id: int
    name: str

    cooldown_manager: "CooldownManager | None" = field(default=None)

    @property
    def mention(self) -> str:
        return f"</{self.name}:{self.id}>"

    def __str__(self) -> str:
        return self.mention

    async def add_cooldown(self, interaction: discord.Interaction["SFABot"]) -> None:
        if self.cooldown_manager is not None:
            await self.cooldown_manager.add_regular_bucket(interaction)

    async def add_changeable_cooldown(self, interaction: discord.Interaction["SFABot"], rate: int, per: int) -> None:
        if self.cooldown_manager is not None:
            await self.cooldown_manager.add_changeable_bucket(interaction, rate, per)
