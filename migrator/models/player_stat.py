from sqlalchemy import BigInteger, Column, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP

from .base import Base

__all__ = [
    "PlayerStat",
]


class PlayerStat(Base):
    """Per-player per-game position stats stored as JSONB."""

    __tablename__ = "player_stat"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    game_id = Column(BigInteger, ForeignKey("game.id", ondelete="CASCADE"), nullable=False)
    season_id = Column(BigInteger, ForeignKey("season.id", ondelete="SET NULL"))
    team_id = Column(BigInteger, ForeignKey("team.id", ondelete="CASCADE"), nullable=False)

    roblox_id = Column(BigInteger, nullable=False)
    player_snowflake = Column(BigInteger, ForeignKey("player.snowflake", ondelete="SET NULL"), nullable=True)

    quarterback = Column(JSONB, nullable=True)
    rushing = Column(JSONB, nullable=True)
    receiver = Column(JSONB, nullable=True)
    corner = Column(JSONB, nullable=True)
    defender = Column(JSONB, nullable=True)
    kicker = Column(JSONB, nullable=True)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_player_stat_box_score", "game_id", "team_id", "roblox_id"),
        Index("idx_player_stat_roblox", "roblox_id"),
        Index("idx_player_stat_season", "season_id"),
    )
