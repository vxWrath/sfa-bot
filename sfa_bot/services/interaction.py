import re
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, ClassVar, Self, final

import discord
from discord.ui import (
    Button,
    DynamicItem,
    File,
    Item,
    MediaGallery,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)
from discord.ui.dynamic import BaseT
from discord.ui.select import BaseSelect
from msgspec import Struct, field

from core import SFAException

if TYPE_CHECKING:
    from .bot import SFABot

__all__ = (
    "BaseItem",
    "BaseLayoutView",
    "BaseView",
    "DeferOptions",
    "InteractionOptions",
    "response",
    "view_interaction_check",
)


class UserOnly(SFAException):
    def __init__(self, *, interaction: bool = False):
        super().__init__(f"This {'interaction' if interaction else 'command'} can only be used by a user.")


class GuildOnly(SFAException):
    def __init__(self, *, interaction: bool = False):
        super().__init__(f"This {'interaction' if interaction else 'command'} can only be used in a guild.")


class MemberOnly(SFAException):
    def __init__(self, *, interaction: bool = False):
        super().__init__(f"This {'interaction' if interaction else 'command'} can only be used by a member.")


class DeferOptions(Struct):
    defer: bool = field(default=False)
    ephemeral: bool = field(default=False)
    thinking: bool = field(default=False)

    def to_bits(self) -> int:
        return (self.defer << 0) | (self.ephemeral << 1) | (self.thinking << 2)


def _shift_bit(value: int, position: int) -> bool:
    return bool((value >> position) & 1)


class InteractionOptions(Struct):
    defer_options: DeferOptions = field(default_factory=DeferOptions)
    modal_response: bool = field(default=False)

    def to_custom_id(self) -> str:
        """Encode options into a 1-char hex string (4 bits).

        Bit layout (LSB → MSB)::

            Bits  0-2  : DeferOptions (defer, ephemeral, thinking)
            Bit   3    : modal_response
        """
        value = self.defer_options.to_bits()  # bits 0-2
        value |= self.modal_response << 3  # bit  3

        return f"{value:01x}"

    @classmethod
    def from_custom_id(cls, custom_id: str) -> Self:
        """Decode a 1-char hex string back into :class:`InteractionOptions`.

        Returns a default instance if the hex string is malformed.
        """
        try:
            value = int(custom_id, 16)
        except ValueError, TypeError:
            return cls()

        defer_options = DeferOptions(
            defer=_shift_bit(value, 0),
            ephemeral=_shift_bit(value, 1),
            thinking=_shift_bit(value, 2),
        )

        modal_response = _shift_bit(value, 3)

        return cls(
            defer_options=defer_options,
            modal_response=modal_response,
        )


BASE_TEMPLATE = r"([0-9a-fA-F])"


class BaseItem(ABC, DynamicItem[BaseT], template=BASE_TEMPLATE):
    checks: ClassVar[list[Callable[[Any, discord.Interaction["SFABot"]], bool]]] = []
    __original_template__: ClassVar[re.Pattern[str]] = re.compile(BASE_TEMPLATE)

    def __init__(self, item: BaseT, *, row: int | None = None, options: InteractionOptions | None = None) -> None:
        super().__init__(item=item, row=row)

        self.options = options or InteractionOptions()

        if isinstance(item, (Button, BaseSelect)):
            if not item.custom_id:
                raise ValueError("Dynamic items must have a custom_id set")

            item.custom_id = f"{self.options.to_custom_id()}:{item.custom_id}"

    def __init_subclass__(cls, *, template: str | re.Pattern[str]) -> None:
        cls.checks = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)

            if attr is not None and callable(attr) and getattr(attr, "__is_check__", False):
                cls.checks.append(attr)  # type: ignore

        compiled_template = re.compile(template) if isinstance(template, str) else template

        # Strip leading ^ and trailing $ anchors so they don't break
        # when the pattern is concatenated with the options prefix.
        clean_pattern = compiled_template.pattern.lstrip("^").rstrip("$")
        cls.__original_template__ = re.compile(clean_pattern)

        return super().__init_subclass__(template=re.compile(BASE_TEMPLATE + ":" + clean_pattern))

    @property
    def template(self) -> re.Pattern[str]:
        """``re.Pattern``: The compiled regular expression that is used to parse the ``custom_id``."""
        return self.__class__.__original_template__

    @classmethod
    @final
    async def from_custom_id(
        cls: type[Self], interaction: discord.Interaction["SFABot"], item: Item[Any], match: re.Match[str], /
    ) -> Self:
        group = match.group(1)
        options = InteractionOptions.from_custom_id(group)

        # Re-match without the options segment
        new_match = cls.__original_template__.match(match.string, len(group) + 1, match.end())

        if not new_match:
            # This should never happen
            raise ValueError("Failed to parse interaction after removing options segment")

        # Store options in extras so they can be accessed in interaction_check
        interaction.extras["options"] = options

        self = await cls.build(interaction, item, new_match)
        self.options = options

        return self

    @classmethod
    @abstractmethod
    async def build(
        cls: type[Self], interaction: discord.Interaction["SFABot"], item: Item[Any], match: re.Match[str], /
    ) -> Self:
        raise NotImplementedError(
            "Dynamic items must implement build() method to parse custom_id and return an instance"
        )

    def require_guild(self, interaction: discord.Interaction["SFABot"]) -> discord.Guild:
        if interaction.guild is None:
            raise GuildOnly(interaction=True)

        return interaction.guild

    def require_user(self, interaction: discord.Interaction["SFABot"]) -> discord.User:
        if interaction.user is None or not isinstance(interaction.user, discord.User):
            raise UserOnly(interaction=True)

        return interaction.user

    def require_member(self, interaction: discord.Interaction["SFABot"]) -> discord.Member:
        if interaction.user is None or not isinstance(interaction.user, discord.Member):
            raise MemberOnly(interaction=True)

        return interaction.user

    async def interaction_check(self, interaction: discord.Interaction["SFABot"]) -> bool:
        interaction.extras["options"] = self.options

        if not await interaction.client.tree.interaction_check(interaction):
            return False

        if interaction.channel and interaction.channel.type == discord.ChannelType.private:
            return True

        for check in self.checks:
            if not await discord.utils.maybe_coroutine(check, self, interaction):
                return False

        return True


class BaseView(discord.ui.View):
    children: list[DynamicItem[Button[Self] | BaseSelect[Self]]]

    async def on_error(self, interaction: discord.Interaction["SFABot"], error: Exception, _: Item[Any]) -> None:
        return await interaction.client.tree.on_error(interaction, error)  # type: ignore


class BaseLayoutView(discord.ui.LayoutView):
    children: list[
        DynamicItem[Button[Self] | BaseSelect[Self]]
        | File[Self]
        | MediaGallery[Self]
        | Section[Self]
        | Separator[Self]
        | TextDisplay[Self]
        | Thumbnail[Self]
    ]

    async def on_error(self, interaction: discord.Interaction["SFABot"], error: Exception, _: Item[Any]) -> None:
        return await interaction.client.tree.on_error(interaction, error)  # type: ignore


def view_interaction_check(func: Callable[[Any, discord.Interaction["SFABot"]], bool | Awaitable[bool]]):
    """Mark a method as a check for a BaseItem."""
    func.__is_check__ = True
    return func


class response:
    @staticmethod
    async def send(
        interaction: discord.Interaction["SFABot"], **kwargs: Any
    ) -> discord.InteractionCallbackResponse["SFABot"] | discord.WebhookMessage:
        if interaction.response.is_done():
            return await interaction.followup.send(**kwargs)
        else:
            return await interaction.response.send_message(**kwargs)

    @staticmethod
    async def edit(
        interaction: discord.Interaction["SFABot"], **kwargs: Any
    ) -> discord.InteractionCallbackResponse["SFABot"] | discord.InteractionMessage | None:
        if interaction.response.is_done():
            return await interaction.edit_original_response(**kwargs)
        else:
            return await interaction.response.edit_message(**kwargs)
