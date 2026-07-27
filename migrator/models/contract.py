from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Index, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from .base import Base

__all__ = [
    "Contract",
]


class Contract(Base):
    """Active roster contract record.

    length_type enum: 0=games, 1=weeks, 2=months, 3=seasons
    """

    __tablename__ = "contract"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    player_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="RESTRICT"), nullable=False)
    team_id = Column(BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=False)

    amount = Column(Numeric)
    notes = Column(Text, nullable=False)
    length = Column(Integer, nullable=False)
    length_type = Column(Integer, nullable=False)

    started_at = Column(TIMESTAMP(timezone=True))
    expires_at = Column(TIMESTAMP(timezone=True))

    terminated_at = Column(TIMESTAMP(timezone=True))
    termination_justification = Column(JSONB)

    is_active = Column(Boolean, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_contract_player_active", "player_snowflake", "is_active"),
        Index("idx_contract_team", "team_id"),
    )
