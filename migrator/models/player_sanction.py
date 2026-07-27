from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from .base import Base

__all__ = [
    "PlayerSanction",
]


class PlayerSanction(Base):
    """Suspensions and team-owner blacklists.

    sanction_type enum: 0=suspension, 1=team owner blacklist
    """

    __tablename__ = "player_sanction"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    player_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="CASCADE"), nullable=False)

    sanction_type = Column(Integer, nullable=False)
    moderator_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="SET NULL"))

    sanctioned_until = Column(TIMESTAMP(timezone=True))
    sanctioned_at = Column(TIMESTAMP(timezone=True))
    justification = Column(JSONB)
    banned_until = Column(TIMESTAMP(timezone=True))

    is_active = Column(Boolean, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_sanction_player_type", "player_snowflake", "sanction_type"),
        Index("idx_sanction_active", "is_active"),
        Index("idx_sanction_type_active", "sanction_type", "is_active"),
    )
