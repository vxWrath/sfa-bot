from sqlalchemy import BigInteger, Column, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "AwardAssignment",
]


class AwardAssignment(Base):
    """Awards granted to players or teams."""

    __tablename__ = "award_assignment"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    award_id = Column(BigInteger, ForeignKey("award.id", ondelete="CASCADE"), nullable=False)
    player_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="CASCADE"), nullable=True)
    team_id = Column(BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_award_assign_award", "award_id"),
        Index("idx_award_assign_player", "player_snowflake"),
        Index("idx_award_assign_team", "team_id"),
        Index(
            "idx_award_assign_unique_player",
            "award_id",
            "player_snowflake",
            unique=True,
            postgresql_where=text("player_snowflake IS NOT NULL"),
        ),
        Index(
            "idx_award_assign_unique_team",
            "award_id",
            "team_id",
            unique=True,
            postgresql_where=text("team_id IS NOT NULL"),
        ),
    )
