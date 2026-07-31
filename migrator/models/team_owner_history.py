from sqlalchemy import BigInteger, Boolean, Column, ForeignKey
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "TeamOwnerHistory",
]


class TeamOwnerHistory(Base):
    """Ownership change log - tracks who owned a team and when."""

    __tablename__ = "team_owner_history"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    player_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="CASCADE"), nullable=False)
    team_id = Column(BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=False)

    appointed_at = Column(TIMESTAMP(timezone=True), nullable=False)
    unappointed_at = Column(TIMESTAMP(timezone=True))
    is_active = Column(Boolean, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
