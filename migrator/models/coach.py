from sqlalchemy import BigInteger, Column, Integer, Text
from sqlalchemy.dialects.postgresql import TIMESTAMP

from .base import Base

__all__ = [
    "Coach",
]


class Coach(Base):
    """Person-based coaching staff."""

    __tablename__ = "coach"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    role_snowflake = Column(BigInteger)
    role_name = Column(Text, nullable=False)
    acronym = Column(Text, nullable=False)
    sort_index = Column(Integer)

    created_at = Column(TIMESTAMP(timezone=True), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False)
