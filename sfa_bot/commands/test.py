import re
from os import urandom
from typing import Literal

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
    view_interaction_check,
)


class TestButton(BaseItem[ui.Button["TestView"]], template=r"button:[^:]+:[a-f0-9]{8}"):
    def __init__(self, action: str, item_hex: str | None = None) -> None:
        super().__init__(
            ui.Button(
                label=f"Say {action.capitalize()}",
                custom_id=f"button:{action}:{item_hex or urandom(4).hex()}",
                style=discord.ButtonStyle.primary,
            ),
            options=InteractionOptions(
                defer_options=DeferOptions(defer=False, ephemeral=True, thinking=False),
            ),
        )

        self.action = action

    @classmethod
    async def build(cls, interaction: discord.Interaction, item: ui.Button["TestView"], match: re.Match[str], /):
        _, action, item_hex = match.group(0).split(":")
        return cls(action=action, item_hex=item_hex)

    async def callback(self, interaction: discord.Interaction[SFABot]) -> None:
        if self.action == "hello":
            content = "Hello!"
        elif self.action == "goodbye":
            content = "Goodbye!"
        else:
            content = f"Unknown action: {self.action}"

        await response.send(interaction, content=content, ephemeral=True)


class ColorSelect(BaseItem[ui.Select["TestView"]], template=r"color:\d{15,25}:[a-f0-9]{8}"):
    def __init__(self, user_id: int, item_hex: str | None = None) -> None:
        super().__init__(
            ui.Select(
                placeholder="Select a color",
                custom_id=f"color:{user_id}:{item_hex or urandom(4).hex()}",
                options=[
                    discord.SelectOption(label="Red", value="red"),
                    discord.SelectOption(label="Blue", value="blue"),
                    discord.SelectOption(label="Green", value="green"),
                ],
            ),
            options=InteractionOptions(
                defer_options=DeferOptions(defer=False, ephemeral=True, thinking=False),
            ),
        )

    @classmethod
    async def build(cls, interaction: discord.Interaction, item: ui.Select["TestView"], match: re.Match[str], /):
        _, user_id, item_hex = match.group(0).split(":")

        interaction.extras["user_id"] = int(user_id)
        return cls(user_id=int(user_id), item_hex=item_hex)

    async def callback(self, interaction: discord.Interaction[SFABot]) -> None:
        color = self.item.values[0]
        await response.send(interaction, content=f"You selected {color}!", ephemeral=True)

    @view_interaction_check
    async def check_user(self, interaction: discord.Interaction[SFABot]) -> bool:
        user_id = interaction.extras.get("user_id")

        if interaction.user.id == user_id:
            return True

        await response.send(interaction, content="You cannot use this select menu.", ephemeral=True)
        return False


class TestView(BaseView):
    def __init__(self, user_id: int) -> None:
        super().__init__()

        self.add_item(ColorSelect(user_id=user_id))
        self.add_item(TestButton("hello"))
        self.add_item(TestButton("goodbye"))


class Layout(ui.LayoutView):
    def __init__(self) -> None:
        super().__init__()

        action_row = discord.ui.ActionRow()
        action_row.add_item(TestButton("hello"))
        self.add_item(action_row)

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(
                    "Click the above button to receive a **very special** message!",
                ),
                accent_colour=discord.Colour.blurple(),
            )
        )


class Test(commands.Cog):
    def __init__(self, bot: SFABot):
        self.bot = bot

    @app_commands.command(
        name="test",
        description="A test command for developers.",
        extras={
            "options": InteractionOptions(
                defer_options=DeferOptions(defer=False, ephemeral=False, thinking=True),
            )
        },
    )
    @app_commands.guild_only()
    @developer_only()
    async def test(self, interaction: discord.Interaction[SFABot], view: Literal["normal", "layout"]) -> None:
        """A test command for developers."""

        if view == "normal":
            test_view = TestView(user_id=interaction.user.id)

            await response.send(
                interaction,
                content="Select an action or use buttons:",
                view=test_view,
            )
        elif view == "layout":
            layout = Layout()

            await response.send(interaction, view=layout)


async def setup(bot: SFABot):
    cog = Test(bot)
    await bot.add_cog(cog)
