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
    configure_root_logger,
    get_env,
    get_logger,
    install_asyncio_exception_handler,
    install_excepthook,
)


def shutdown(bot: SFABot):
    logger = get_logger("main")
    logger.warning("Received shutdown signal, exiting...")

    try:
        bot.loop.create_task(bot.close())
    except RuntimeError:
        logger.error("Event loop already closed, cannot close bot gracefully")


async def main() -> None:
    configure_root_logger()
    install_excepthook()
    install_asyncio_exception_handler()

    logger = get_logger("main")

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


if __name__ == "__main__":
    asyncio.run(main())
