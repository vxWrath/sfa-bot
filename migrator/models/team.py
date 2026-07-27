from sqlalchemy import BigInteger, Boolean, Column, Integer, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "Team",
]


class Team(Base):
    """Franchise with division tracking."""

    __tablename__ = "team"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    role_snowflake = Column(BigInteger, nullable=True)
    role_name = Column(Text, nullable=False)

    division = Column(Integer, nullable=True)
    subdivision = Column(Integer, nullable=True)
    gsp = Column(Integer, nullable=True)

    is_active = Column(Boolean, nullable=False)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
