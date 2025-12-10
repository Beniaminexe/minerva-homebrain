from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Integer, String

from ..core.database import Base


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, unique=True, nullable=False)
    definition = Column(String, nullable=False)

    # We'll keep extra JSON as a plain string for now (can upgrade later)
    extra_json = Column(String, nullable=True)

    active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
