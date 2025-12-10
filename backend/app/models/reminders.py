from datetime import datetime, time
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Time, ForeignKey
from sqlalchemy.orm import relationship
from ..core.database import Base



class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)
    description = Column(String, nullable=True)

    schedule_kind = Column(String, nullable=False)   # DAILY, WEEKLY, ONE_OFF
    time_of_day = Column(Time, nullable=False)

    days_of_week = Column(String, nullable=True)     # comma-separated "1,3,5"
    one_off_at = Column(DateTime, nullable=True)

    grace_before_min = Column(Integer, default=0)
    grace_after_min = Column(Integer, default=60)

    channels = Column(String, default="telegram,esp32")
    enabled = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    occurrences = relationship("ReminderOccurrence", back_populates="reminder")


class ReminderOccurrence(Base):
    __tablename__ = "reminder_occurrences"

    id = Column(Integer, primary_key=True, index=True)
    reminder_id = Column(Integer, ForeignKey("reminders.id"))

    due_at = Column(DateTime, nullable=False)
    window_start_at = Column(DateTime, nullable=False)
    window_end_at = Column(DateTime, nullable=False)

    state = Column(String, default="PENDING")  # PENDING | DONE | MISSED | SKIPPED

    done_at = Column(DateTime, nullable=True)
    skipped_at = Column(DateTime, nullable=True)
    note = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    reminder = relationship("Reminder", back_populates="occurrences")
