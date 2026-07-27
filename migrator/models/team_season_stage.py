from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "TeamSeasonStage",
]


class TeamSeasonStage(Base):
    """Per-stage snapshot: division, playoff round, or championship placement.

    One row per team per season per stage (1-9).
    Stages 1-5 are group stages, 6-9 are playoff rounds.
    """

    __tablename__ = "team_season_stage"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    season_id = Column(BigInteger, ForeignKey("season.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=False)
    stage = Column(Integer, nullable=False)

    division = Column(Integer, nullable=True)
    subdivision = Column(Text, nullable=True)
    gsp = Column(Integer, nullable=True)

    is_play_in = Column(Boolean, nullable=True)
    is_auto_qualified = Column(Boolean, nullable=True)
    is_champion = Column(Boolean, nullable=False, default=False)

    is_finished = Column(Boolean)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("season_id", "team_id", "stage", name="idx_season_team_unique"),
        Index("idx_season_team_stage", "season_id", "stage"),
        Index("idx_season_team_team", "team_id"),
    )
