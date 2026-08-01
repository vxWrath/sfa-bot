import asyncio
import signal

import aiohttp
from services import (
    SFABot,
    setup_discord_logger,
)

from core import (
    Cache,
    Database,
    League,
    get_env,
    get_logger,
    install_asyncio_exception_handler,
    install_excepthook,
)

logger = get_logger("main")

try:
    import uvloop  # type: ignore

    loop_factory = uvloop.new_event_loop
    logger.info("Using uvloop")

except ImportError:
    loop_factory = None
    logger.info("Using asyncio")


def shutdown(bot: SFABot):
    logger.warning("Received shutdown signal, exiting...")

    try:
        bot.loop.create_task(bot.close())
    except RuntimeError:
        logger.error("Event loop already closed, cannot close bot gracefully")


async def main() -> None:
    install_excepthook()
    install_asyncio_exception_handler()

    token = get_env("DISCORD_TOKEN")

    logger.info("Initializing bot")

    League.load()
    bot = SFABot()
    bot.cache = Cache()
    bot.database = Database()
    bot.session = aiohttp.ClientSession()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown, bot)

    setup_discord_logger()

    await bot.cache.connect()
    await bot.database.connect()

    bot.super_init()

    async with bot:
        try:
            await bot.login(token)
            logger.info("Logged in as %s", bot.user)

            await bot.connect()
        except Exception as e:
            logger.critical("Failed to start bot", exc_info=e)
            raise

    logger.info("Shutting down")
    await bot.session.close()
    await bot.database.close()
    await bot.cache.close()

    if bot._closing_task is not None:
        await bot._closing_task

    logger.info("Bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=loop_factory)
