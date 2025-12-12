from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from ..core.database import Base


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(String, nullable=False)
    payload_json = Column(Text, nullable=False)
    status = Column(String, default="PENDING")  # PENDING | SENDING | FAILED | SENT
    attempt_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)

    locked_at = Column(DateTime, nullable=True)
    locked_by = Column(String, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    acked_at = Column(DateTime, nullable=True)
