import asyncio
from collections.abc import Awaitable

from core import get_logger

logger = get_logger("utils")


def create_logged_task[T](
    coro: Awaitable[T], *, name: str | None = None, suppress_cancelled: bool = False
) -> asyncio.Task[T]:
    """Wraps an asyncio.task for logging exceptions"""

    name = name or getattr(coro, "__name__", repr(coro))

    async def wrapper():
        try:
            return await coro
        except asyncio.CancelledError as e:
            if not suppress_cancelled:
                logger.warning(f"Task '{name}' was cancelled.", exc_info=e)
            raise e
        except Exception as e:
            logger.error(f"Task '{name}' raised an exception", exc_info=e)
            raise e

    task = asyncio.create_task(wrapper(), name=name)
    return task
