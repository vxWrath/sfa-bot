import asyncio

from core import (
    League,
    get_logger,
    install_asyncio_exception_handler,
    install_excepthook,
)


async def main() -> None:
    League.load()

    install_excepthook()
    install_asyncio_exception_handler()

    logger = get_logger("main")
    logger.info("It Works!")


if __name__ == "__main__":
    asyncio.run(main())
