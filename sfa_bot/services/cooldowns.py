import hashlib
import time
from collections.abc import Callable, Coroutine, Hashable
from typing import (
    Literal,
    TypeVar,
    cast,
    overload,
)

import discord
from discord.app_commands.commands import CheckInputParameter, Command, ContextMenu
from discord.app_commands.errors import CommandOnCooldown
from msgspec import Struct, field

from core import get_logger

from .bot import SFABot

__all__ = ["Cooldown", "CooldownManager", "changeable_cooldown", "cooldown"]

logger = get_logger("cooldowns")

T = TypeVar("T")

CooldownFuncReturn = T | Coroutine[None, None, T]
CooldownKey = Callable[[discord.Interaction[SFABot]], CooldownFuncReturn[T]]

RegularCooldownFactory = Callable[[discord.Interaction[SFABot]], CooldownFuncReturn[T]]
ChangeableCooldownFactory = Callable[[discord.Interaction[SFABot], int, int], CooldownFuncReturn[T]]


class Cooldown(Struct):
    rate: int  # attempts possible
    per: int  # how many attemps every certain amount of time

    window: float = field(default=0.0)  # time of first attempt
    tokens: int | None = field(default=None)  # attempts left
    last: float = field(default=0.0)  # time of latest attempt

    def __post_init__(self):
        if self.tokens is None:
            self.tokens = self.rate

    def get_tokens(self, current_time: float | None = None) -> int:
        if self.tokens is None:
            raise ValueError("Cooldown bucket is missing tokens value")

        current_time = current_time or time.time()
        tokens_left = max(self.tokens, 0)

        if current_time > self.window + self.per:
            tokens_left = self.rate

        return tokens_left

    def get_retry_after(self, current_time: float | None = None) -> float:
        current_time = current_time or time.time()
        tokens = self.get_tokens(current_time)

        if tokens == 0:
            return self.per - (current_time - self.window)
        return 0.0

    def update_rate_limit(self, current_time: float | None = None, *, tokens: int = 1) -> float | None:
        current_time = current_time or time.time()
        self.last = current_time

        self.tokens = self.get_tokens(current_time)

        if self.tokens == self.rate:
            self.window = current_time

        self.tokens -= tokens

        if self.tokens < 0:
            return self.per - (current_time - self.window)
        return None


class CooldownManager:
    @overload
    def __init__(
        self,
        key: CooldownKey[Hashable],
        factory: RegularCooldownFactory[Cooldown | None],
        *,
        rate: int,
        per: int,
        changeable: Literal[False],
        premium_excluded: bool = False,
    ) -> None: ...

    @overload
    def __init__(
        self,
        key: CooldownKey[Hashable],
        factory: ChangeableCooldownFactory[Cooldown | None],
        *,
        rate: int,
        per: int,
        changeable: Literal[True],
        premium_excluded: bool = False,
    ) -> None: ...

    def __init__(
        self,
        key: CooldownKey[Hashable],
        factory: RegularCooldownFactory[Cooldown | None] | ChangeableCooldownFactory[Cooldown | None],
        *,
        rate: int,
        per: int,
        changeable: bool,
        premium_excluded: bool = False,
    ) -> None:
        self.id = ""  # will be set in the decorator

        self.key = key
        self.factory = factory
        self.rate = rate
        self.per = per

        self.changeable = changeable
        self.premium_excluded = premium_excluded

    async def add_regular_bucket(self, interaction: discord.Interaction[SFABot]) -> Cooldown | None:
        key = str(await discord.utils.maybe_coroutine(self.key, interaction))
        bucket = await interaction.client.cache.get("cooldown", self.id, key, cls=Cooldown)

        if bucket is None:
            logger.debug("Creating new cooldown bucket for command=%s key=%s", self.id, key)
            bucket = await discord.utils.maybe_coroutine(
                cast(RegularCooldownFactory[Cooldown], self.factory), interaction
            )

        await interaction.client.cache.set("cooldown", self.id, key, value=bucket, ex=self.per)
        return bucket

    async def add_changeable_bucket(
        self, interaction: discord.Interaction[SFABot], rate: int, per: int
    ) -> Cooldown | None:
        key = str(await discord.utils.maybe_coroutine(self.key, interaction))
        bucket_exists = await interaction.client.cache.redis.exists(f"cooldown:{self.id}:{key}")

        if bucket_exists:
            return None

        bucket = await discord.utils.maybe_coroutine(
            cast(ChangeableCooldownFactory[Cooldown | None], self.factory), interaction, rate, per
        )

        if bucket is not None:
            logger.debug("Creating new changeable cooldown bucket for command=%s key=%s", self.id, key)
            await interaction.client.cache.set("cooldown", self.id, key, value=bucket, ex=per)

    async def get_bucket(self, interaction: discord.Interaction[SFABot]) -> Cooldown | None:
        key = str(await discord.utils.maybe_coroutine(self.key, interaction))
        return await interaction.client.cache.get("cooldown", self.id, key, cls=Cooldown)

    async def predicate(self, interaction: discord.Interaction[SFABot]) -> Literal[True]:
        bucket = await self.get_bucket(interaction)

        if bucket is None:
            return True

        retry_after = bucket.update_rate_limit()

        key = str(await discord.utils.maybe_coroutine(self.key, interaction))
        await interaction.client.cache.set("cooldown", self.id, key, value=bucket, ex=self.per)

        if retry_after is None:
            return True

        logger.debug("Cooldown hit for command=%s key=%s retry_after=%.1fs", self.id, key, retry_after)
        raise CommandOnCooldown(bucket, retry_after)  # type: ignore


def cooldown_check(manager: CooldownManager) -> Callable[[T], T]:
    def decorator(func: CheckInputParameter) -> CheckInputParameter:
        if isinstance(func, (Command, ContextMenu)):
            manager.id = hashlib.md5(func.qualified_name.encode()).hexdigest()

            func.checks.append(manager.predicate)
        else:
            manager.id = hashlib.md5(func.__qualname__.encode()).hexdigest()

            if not hasattr(func, "__discord_app_commands_checks__"):
                func.__discord_app_commands_checks__ = []

            func.__discord_app_commands_checks__.append(manager.predicate)

        func.__cooldown_manager__ = manager  # type: ignore
        return func

    return decorator  # type: ignore


def cooldown(
    rate: int, per: int, *, key: CooldownKey[Hashable] | None = discord.utils.MISSING, premium_excluded: bool = False
) -> Callable[[T], T]:
    if key is discord.utils.MISSING:
        key_func = lambda i: i.user.id
    elif key is None:
        key_func = lambda i: None
    else:
        key_func = key

    factory = lambda i: Cooldown(rate=rate, per=per, window=0.0, tokens=rate, last=0.0)
    manager = CooldownManager(
        key_func, factory, rate=rate, per=per, changeable=False, premium_excluded=premium_excluded
    )

    return cooldown_check(manager)


def changeable_cooldown(
    rate: int, per: int, *, key: CooldownKey[Hashable] | None = discord.utils.MISSING, premium_excluded: bool = False
) -> Callable[[T], T]:
    if key is discord.utils.MISSING:
        key_func = lambda i: i.user.id
    elif key is None:
        key_func = lambda i: None
    else:
        key_func = key

    factory = lambda i, r, p: Cooldown(rate=r, per=p, window=0.0, tokens=r, last=0.0)
    manager = CooldownManager(key_func, factory, rate=rate, per=per, changeable=True, premium_excluded=premium_excluded)

    return cooldown_check(manager)
