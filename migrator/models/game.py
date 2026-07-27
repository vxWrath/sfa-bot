from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from .base import Base

__all__ = [
    "Game",
]


class Game(Base):
    """Match results with referees, streamers, and score reporting."""

    __tablename__ = "game"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    season_id = Column(BigInteger, ForeignKey("season.id", ondelete="CASCADE"), nullable=False)

    home_team_id = Column(BigInteger, ForeignKey("team.id", ondelete="SET NULL"), nullable=True)
    away_team_id = Column(BigInteger, ForeignKey("team.id", ondelete="SET NULL"), nullable=True)

    home_score = Column(Integer)
    away_score = Column(Integer)

    is_forfeit = Column(Boolean, nullable=False)
    is_double_forfeit = Column(Boolean, nullable=False)
    forfeit_by_home = Column(Boolean, nullable=True)
    forfeit_by_away = Column(Boolean, nullable=True)

    stage = Column(Integer, nullable=False)
    division = Column(Integer, nullable=True)
    subdivision = Column(Integer, nullable=True)
    week = Column(Integer, nullable=True)

    scheduled_for = Column(TIMESTAMP(timezone=True), nullable=False)
    thread_snowflake = Column(BigInteger, nullable=False)
    referee_snowflakes = Column(JSONB, nullable=False)
    streamers = Column(JSONB, nullable=False)

    reporter_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="RESTRICT"), nullable=False)
    reported_at = Column(TIMESTAMP(timezone=True), nullable=False)

    approver_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="RESTRICT"))
    approved_at = Column(TIMESTAMP(timezone=True))

    version = Column(Integer, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_game_home_team", "home_team_id"),
        Index("idx_game_away_team", "away_team_id"),
        Index("idx_game_season", "season_id"),
        Index("idx_game_season_home", "season_id", "home_team_id"),
        Index("idx_game_season_away", "season_id", "away_team_id"),
    )
