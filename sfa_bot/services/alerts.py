import enum
from pathlib import Path
from typing import TYPE_CHECKING

import orjson
from msgspec import Struct

from core import get_logger

from .colors import Color

if TYPE_CHECKING:
    from .bot import SFABot

__all__ = ["AlertEvent", "AlertInfo", "_send_alert"]

logger = get_logger("alerts")


class AlertEvent(enum.StrEnum):
    TEAM_OWNER_APPOINTED = "team_owner_appointed_alert"


class AlertInfo(Struct):
    event: AlertEvent
    text: str


ALERTS_PATH = Path("files/alerts.json")
ALERTS: dict[str, AlertInfo] = {
    alert["event"]: AlertInfo(**alert) for alert in orjson.loads(ALERTS_PATH.read_text(encoding="utf-8"))
}


async def _send_alert(bot: "SFABot", event: AlertEvent, color: Color | None = None, **kwargs: str) -> None:
    pass
