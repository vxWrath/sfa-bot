import asyncio
import importlib.util
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any

import aiohttp
import discord
from discord.app_commands import (
    AppCommand,
    AppCommandGroup,
    AppInstallationType,
    Command,
    CommandTree,
    ContextMenu,
    Group,
)
from discord.ext import commands

from core import (
    Cache,
    CommandNotFound,
    Database,
    DotDict,
    League,
    PlayerRow,
    StoredCommand,
    get_env,
    get_logger,
    is_dev,
)

from .alerts import AlertEvent, _send_alert
from .colors import Color
from .interaction import BaseItem, InteractionOptions, response
from .utils import chunk_guild

if TYPE_CHECKING:
    from .cooldowns import CooldownManager

__all__ = ["SFABot"]

logger = get_logger("sfa")

COMMAND_PATH = Path("sfa_bot/commands").resolve()
EVENT_PATH = Path("sfa_bot/events").resolve()

intents = discord.Intents.none()
intents.guilds = True
intents.emojis = True
intents.members = True

member_cache_flags = discord.MemberCacheFlags().none()
member_cache_flags.joined = True


class SFABot(commands.Bot):
    user: discord.ClientUser
    application: discord.AppInfo

    def __init__(
        self,
    ):
        self.cache: Cache
        self.database: Database
        self.session: aiohttp.ClientSession
        self.stored_commands: dict[str, StoredCommand] = {}

    def super_init(self):
        super().__init__(
            tree_cls=Tree,
            command_prefix=[],
            intents=intents,
            member_cache_flags=member_cache_flags,
            max_messages=None,
            chunk_guilds_at_startup=False,
            allowed_installs=AppInstallationType(guild=True, user=False),
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="over SFA",
            ),
        )

    async def setup_hook(self) -> None:
        logger.info("setup_hook starting")
        await self.load_extensions()

        LEAGUE_GUILD = discord.Object(id=League.snowflake, type=discord.Guild)

        sync_sentinel = Path("core/files/.commands_synced")
        if not sync_sentinel.exists():
            if is_dev():
                # Clear global commands
                await self.unload_extensions()
                await self.tree.sync()
                await self.load_extensions()

                # Sync commands to admin guild for testing
                self.tree.copy_global_to(guild=LEAGUE_GUILD)
                app_commands = await self.tree.sync(guild=LEAGUE_GUILD)
            else:
                # Sync commands globally
                app_commands = await self.tree.sync(guild=None)

                # Sync admin commands to admin guild
                await self.tree.sync(guild=LEAGUE_GUILD)

            sync_sentinel.touch()

            logger.info("Initial command sync to admin guild completed.")
        else:
            app_commands = await self.fetch_app_commands()

        self.stored_commands = self.build_command_storage(app_commands)
        self.attach_cooldown_managers()

        embed = discord.Embed(
            description=(
                f"## SFA Bot Started\n`Bot:` **{self.user}** (`{self.user.id}`)\n`Guild:` `{League.snowflake}`\n"
            ),
            color=Color.brand_green(),
            timestamp=discord.utils.utcnow(),
        )

        await _send_to_webhook(self.session, premium=True, embed=embed)

    async def close(self) -> None:
        logger.info("Bot shutting down")

        embed = discord.Embed(
            description=(
                f"## SFA Bot Stopped\n`Bot:` **{self.user}** (`{self.user.id}`)\n`Guild:` `{League.snowflake}`\n"
            ),
            color=Color.brand_red(),
            timestamp=discord.utils.utcnow(),
        )

        await _send_to_webhook(self.session, premium=True, embed=embed)

        return await super().close()

    async def load_extensions(self) -> None:
        self.cog_names: list[str] = []

        for file_path in COMMAND_PATH.rglob("*.py"):
            relative_path = file_path.relative_to(COMMAND_PATH.parent).with_suffix("")
            cog_path = ".".join(relative_path.parts)

            self.cog_names.append(cog_path)

            try:
                await self.reload_extension(cog_path)
            except commands.ExtensionNotLoaded:
                await self.load_extension(cog_path)

            logger.debug(f"Loaded extension {cog_path!r}")
            self._load_dynamic_item(cog_path)

        for file_path in EVENT_PATH.rglob("*.py"):
            relative_path = file_path.relative_to(EVENT_PATH.parent).with_suffix("")
            cog_path = ".".join(relative_path.parts)

            try:
                await self.reload_extension(cog_path)
            except commands.ExtensionNotLoaded:
                await self.load_extension(cog_path)

            logger.debug(f"Loaded extension {cog_path!r}")

        return None

    def _load_dynamic_item(self, module_path: str) -> None:
        spec = importlib.util.find_spec(module_path)
        if not spec or not spec.loader:
            logger.warning(f"Unable to load module '{module_path}' for dynamic items")
            return

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        for obj in module.__dict__.values():
            if not isinstance(obj, type):
                continue

            if issubclass(obj, discord.ui.DynamicItem) and obj is not discord.ui.DynamicItem and obj is not BaseItem:
                self.add_dynamic_items(obj)
                logger.debug(
                    f"Registered dynamic item {obj.__name__!r} with pattern '{obj.__discord_ui_compiled_template__.pattern}'"
                )

    async def unload_extensions(self) -> None:
        for i in range(0, len(self.cog_names)):
            try:
                await self.unload_extension(self.cog_names[i])
            except commands.ExtensionNotLoaded:
                pass

        return None

    def build_command_storage(self, commands: Sequence[AppCommand | AppCommandGroup]) -> dict[str, StoredCommand]:
        """Convert discord AppCommand/AppCommandGroup objects to StoredCommands without writing to Redis."""

        stored_commands: dict[str, StoredCommand] = {}
        for command in self._flatten_app_commands_recursively(commands):
            if isinstance(command, AppCommand):
                root = command
            elif isinstance(command.parent, AppCommand):
                root = command.parent
            elif isinstance(command.parent.parent, AppCommand):
                root = command.parent.parent
            else:
                raise ValueError("Impossible")

            name = getattr(command, "qualified_name", command.name)
            stored_commands[name] = StoredCommand(id=root.id, name=name)

        return stored_commands

    async def fetch_app_commands(
        self, *, guild: discord.Object | None = discord.utils.MISSING
    ) -> Sequence[AppCommand | AppCommandGroup]:
        """Fetch global commands from Discord and flatten subcommands into a single list."""

        if guild is discord.utils.MISSING:
            guild = discord.Object(id=League.snowflake, type=discord.Guild) if is_dev() else None

        return await self.tree.fetch_commands(guild=guild)

    def _flatten_app_commands_recursively(
        self, entities: Sequence[AppCommand | AppCommandGroup]
    ) -> Sequence[AppCommand | AppCommandGroup]:
        commands = []
        for entity in entities:
            is_group = any(isinstance(opt, AppCommandGroup) for opt in entity.options)

            if is_group:
                commands.extend(self._flatten_app_commands_recursively(entity.options))  # type: ignore
            else:
                commands.append(entity)

        return commands

    def attach_cooldown_managers(self) -> None:
        cooldown_managers: dict[str, "CooldownManager"] = {}
        self.get_cooldown_managers(cooldown_managers, self.tree.get_commands(guild=None))

        for command_name, manager in cooldown_managers.items():
            success = False
            if command := self.stored_commands.get(command_name):
                command.cooldown_manager = manager
                success = True

            logger.info(f"Attached cooldown manager to command '{command_name}': {'Success' if success else 'Failed'}")

    def get_cooldown_managers(
        self,
        cooldown_managers: dict[str, "CooldownManager"],
        entities: Sequence[Command[Any, ..., Any] | Group | ContextMenu],
    ) -> None:
        for entity in entities:
            if isinstance(entity, Command):
                manager = getattr(entity.callback, "__cooldown_manager__", None)

                if manager is not None:
                    cooldown_managers[entity.qualified_name] = manager

            elif isinstance(entity, Group):
                self.get_cooldown_managers(cooldown_managers, entity.commands)

    def retrieve_command(self, name: str) -> StoredCommand:
        """Retrieve a StoredCommand by name from the in-memory store."""
        try:
            return self.stored_commands[name]
        except KeyError:
            raise CommandNotFound(name) from None

    async def send_alert(self, league: League, event: AlertEvent, color: Color | None = None, **kwargs: str) -> None:
        await _send_alert(self, league, event, color=color, **kwargs)


async def _send_to_webhook(session: aiohttp.ClientSession, premium: bool, embed: discord.Embed):
    url = get_env("PREMIUM_CONTAINERS_WEBHOOK_URL") if premium else get_env("PEERLESS_CLUSTERS_WEBHOOK_URL")

    try:
        async with session.post(url, json={"embeds": [embed.to_dict()]}) as resp:
            resp.raise_for_status()
    except Exception as e:
        logger.error("Failed to send webhook (%s)", "premium" if premium else "cluster", exc_info=e)


class Tree(CommandTree[SFABot]):
    async def interaction_check(self, interaction: discord.Interaction[SFABot]) -> bool:
        guild_id = interaction.guild.id if interaction.guild else "DM"
        command_name = interaction.command.qualified_name if interaction.command else "unknown"
        logger.debug("Checking interaction %s in %s", command_name, guild_id)

        if not self.client.is_ready():
            await interaction.response.send_message(
                content="**The bot is not ready yet. Please try again in a few moments.**", ephemeral=True
            )
            return False

        if interaction.guild and interaction.guild.unavailable:
            try:
                await response.send(
                    interaction, content="**This server is unavailable. This is a discord issue.**", ephemeral=True
                )
            except discord.HTTPException:
                pass

            return False

        data: DotDict[str, DotDict[str, Any]] = DotDict(interaction.data) if interaction.data else DotDict()  # type: ignore

        if interaction.command:
            options: InteractionOptions = interaction.command.extras.get("options", InteractionOptions())
        else:
            options: InteractionOptions = interaction.extras.get("options", InteractionOptions())

        if not options.modal_response and options.defer_options.defer:
            await interaction.response.defer(
                ephemeral=options.defer_options.ephemeral, thinking=options.defer_options.thinking
            )

        chunk_future: asyncio.Future[list[discord.Member]] | None = None

        if interaction.guild:
            if not interaction.guild.chunked:
                chunk_future = await chunk_guild(interaction.guild, wait=False)

                if not options.modal_response and not options.defer_options.defer:
                    await interaction.response.defer(
                        ephemeral=options.defer_options.ephemeral, thinking=options.defer_options.thinking
                    )

        player_ids: set[int] = set()
        if options.player_keys is not None:
            interaction.extras["players"] = {}
            player_ids.add(interaction.user.id)

            if data.has("resolved"):
                for user_id, discord_user_data in (
                    data.resolved.get("members") or data.resolved.get("users", {})
                ).items():
                    if (
                        interaction.user.id == int(user_id)
                        or discord_user_data.get("bot", False)
                        or discord_user_data.get("user", {}).get("bot", False)
                    ):
                        continue

                    player_ids.add(int(user_id))

        if chunk_future is not None or player_ids:
            try:
                async with asyncio.timeout(15 if interaction.response.is_done() else 1.5):
                    if player_ids:
                        repo = self.client.database.get_repository(PlayerRow)
                        players = await asyncio.shield(asyncio.gather(*(repo.produce_player(x) for x in player_ids)))

                        for player in players:
                            interaction.extras["players"][player.id] = player

                    if chunk_future is not None:
                        await asyncio.shield(chunk_future)

            except TimeoutError:
                logger.warning("Timeout while fetching data.")
                return False

        return True

    async def on_error(self, interaction: discord.Interaction[SFABot], error: Exception) -> None:
        logger.error("Command error", exc_info=error)

        await response.send(
            interaction, content=f"```py\n{''.join(traceback.format_exception(error))}```", ephemeral=True
        )
        return None
