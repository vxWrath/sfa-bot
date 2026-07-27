from sqlalchemy import BigInteger, Column
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "Player",
]


class Player(Base):
    """Discord user linked to a Roblox account."""

    __tablename__ = "player"

    snowflake = Column(BigInteger, primary_key=True)
    roblox_id = Column(BigInteger, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
