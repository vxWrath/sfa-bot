import asyncio
from typing import Literal, overload

import discord

from core import get_logger

__all__ = ["MINIMUM_PERMISSIONS", "chunk_guild"]

logger = get_logger("peerless.utils")


@overload
async def chunk_guild(guild: discord.Guild, *, wait: Literal[True] = ...) -> list[discord.Member]: ...


@overload
async def chunk_guild(guild: discord.Guild, *, wait: Literal[False] = ...) -> asyncio.Future[list[discord.Member]]: ...


async def chunk_guild(
    guild: discord.Guild, *, wait: bool = True
) -> list[discord.Member] | asyncio.Future[list[discord.Member]]:
    state = guild._state

    if not state._intents.members:
        raise discord.ClientException("Intents.members must be enabled to use this.")

    if state.is_guild_evicted(guild):
        raise discord.ClientException("Guild is evicted, unable to chunk members.")

    logger.debug(f"Chunking guild {guild.id} ({guild.name}) with wait={wait}")
    return await state.chunk_guild(guild, wait=wait, cache=True)


MINIMUM_PERMISSIONS = {
    p: status
    for p, status in discord.Permissions(
        view_channel=True, send_messages=True, embed_links=True, read_message_history=True
    )
    if status
}
