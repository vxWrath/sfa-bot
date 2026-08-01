import re
from os import urandom

import discord
from discord import app_commands, ui
from discord.ext import commands
from services import (
    BaseItem,
    BaseView,
    DeferOptions,
    InteractionOptions,
    SFABot,
    developer_only,
    response,
)

from core import get_logger

logger = get_logger("command-sync")


class ConfigSelect(BaseItem[ui.Select["ConfigView"]], template="^sync:[a-f0-9]{8}$"):
    def __init__(self, item_hex: str | None = None) -> None:
        super().__init__(
            ui.Select(
                placeholder="Select a config",
                custom_id=f"sync:{item_hex or urandom(4).hex()}",
                options=[
                    discord.SelectOption(label="Reload Extensions", value="reload"),
                    discord.SelectOption(label="Sync Extensions", value="sync"),
                    discord.SelectOption(label="Globally Sync Extensions", value="sync_global"),
                    discord.SelectOption(label="Reload Extensions & Sync Commands", value="reload_sync"),
                ],
            ),
            options=InteractionOptions(
                defer_options=DeferOptions(defer=False, ephemeral=True, thinking=False),
            ),
        )

    @classmethod
    async def build(cls, interaction: discord.Interaction, item: ui.Select["ConfigView"], match: re.Match[str], /):
        item_hex = match.group(0).split(":")[1]
        return cls(item_hex=item_hex)

    async def callback(self, interaction: discord.Interaction[SFABot]) -> None:
        guild = self.require_guild(interaction)

        command = self.item.values[0]
        option = next(x for x in self.item.options if x.value == command)

        option.default = False

        await response.edit(interaction, view=self.view)

        try:
            if command == "reload":
                await interaction.client.load_extensions()

            elif command == "sync":
                g = discord.Object(id=guild.id)

                interaction.client.tree.copy_global_to(guild=g)
                app_commands = await interaction.client.tree.sync(guild=g)

                interaction.client.build_command_storage(app_commands)
                interaction.client.attach_cooldown_managers()

            elif command == "sync_global":
                app_commands = await interaction.client.tree.sync(guild=None)

                interaction.client.build_command_storage(app_commands)
                interaction.client.attach_cooldown_managers()
            else:
                await interaction.client.load_extensions()

                interaction.client.tree.copy_global_to(guild=discord.Object(id=guild.id))
                app_commands = await interaction.client.tree.sync(guild=discord.Object(id=guild.id))

                interaction.client.build_command_storage(app_commands)
                interaction.client.attach_cooldown_managers()
        except Exception as e:
            logger.error(f"Failed to execute `{command}` command", exc_info=e)
            await response.send(interaction, content=f"Failed to execute `{command}` command", ephemeral=True)
            return

        await response.send(interaction, content=f"Successfully executed `{command}` command.", ephemeral=True)


class ConfigView(BaseView):
    def __init__(self) -> None:
        super().__init__()

        self.add_item(ConfigSelect())


class Sync(commands.Cog):
    def __init__(self, bot: SFABot):
        self.bot = bot

    @app_commands.command(
        name="sync",
        description="Sync the bot's commands with Discord",
        extras={
            "options": InteractionOptions(
                defer_options=DeferOptions(defer=False, ephemeral=True, thinking=True),
            )
        },
    )
    @app_commands.guild_only()
    @developer_only()
    async def sync(self, interaction: discord.Interaction[SFABot]) -> None:
        """Sync the bot's commands with Discord."""

        view = ConfigView()
        await response.send(interaction, view=view, ephemeral=True)


async def setup(bot: SFABot):
    cog = Sync(bot)
    await bot.add_cog(cog)
