from sqlalchemy import BigInteger, Boolean, Column, Integer
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "Season",
]


class Season(Base):
    """Season & stage tracking.

    current_stage enum:
      1=GROUP_1, 2=GROUP_2, 3=GROUP_3, 4=GROUP_4, 5=GROUP_5,
      6=PLAYOFFS_R1, 7=PLAYOFFS_QF, 8=PLAYOFFS_SF, 9=PLAYOFFS_FINAL
    """

    __tablename__ = "season"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    season_number = Column(Integer, nullable=False)
    current_stage = Column(Integer, nullable=False, default=1)

    is_playoffs = Column(Boolean, nullable=False, default=False)

    is_active = Column(Boolean, nullable=False, default=True)
    version = Column(Integer, nullable=False, default=1)

    started_at = Column(TIMESTAMP(timezone=True))
    ended_at = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
