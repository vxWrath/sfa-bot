import datetime

from msgspec import Struct, field

__all__ = [
    "SeasonRow",
]


class SeasonRow(Struct, dict=True, kw_only=True):
    """Season & stage tracking.

    current_stage enum:
      1=GROUP_1, 2=GROUP_2, 3=GROUP_3, 4=GROUP_4, 5=GROUP_5,
      6=PLAYOFFS_R1, 7=PLAYOFFS_QF, 8=PLAYOFFS_SF, 9=PLAYOFFS_FINAL
    """

    id: int
    season_number: int
    current_stage: int = field(default=1)

    is_playoffs: bool = field(default=False)

    is_active: bool = field(default=True)
    version: int = field(default=1)

    started_at: datetime.datetime | None = field(default=None)
    ended_at: datetime.datetime | None = field(default=None)

    created_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
    updated_at: datetime.datetime = field(default_factory=lambda: datetime.datetime.now(datetime.UTC))
