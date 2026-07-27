from sqlalchemy import BigInteger, Column, ForeignKey, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "Award",
]


class Award(Base):
    """Custom awards - can be seasonal or HOF-style (no season)."""

    __tablename__ = "award"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    season_id = Column(BigInteger, ForeignKey("season.id", ondelete="CASCADE"), nullable=True)
    name = Column(Text, nullable=False)
    category = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    role_snowflake = Column(BigInteger)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
