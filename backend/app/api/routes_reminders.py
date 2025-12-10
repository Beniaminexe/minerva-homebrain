from datetime import datetime, date, time as time_type
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import Reminder, ReminderOccurrence

router = APIRouter(prefix="/reminders", tags=["reminders"])


# ---------- Pydantic schemas ----------

class ReminderBase(BaseModel):
    label: str
    description: Optional[str] = None
    schedule_kind: str  # DAILY, WEEKLY, ONE_OFF
    time_of_day: str    # "HH:MM"
    days_of_week: Optional[List[int]] = None  # 0=Mon .. 6=Sun
    one_off_at: Optional[datetime] = None
    grace_before_min: int = 0
    grace_after_min: int = 60
    channels: Optional[List[str]] = ["telegram", "esp32"]
    enabled: bool = True

    @field_validator("schedule_kind")
    @classmethod
    def validate_schedule_kind(cls, v: str) -> str:
        allowed = {"DAILY", "WEEKLY", "ONE_OFF"}
        v_up = v.upper()
        if v_up not in allowed:
            raise ValueError(f"schedule_kind must be one of {allowed}")
        return v_up

    @field_validator("time_of_day")
    @classmethod
    def validate_time(cls, v: str) -> str:
        # basic sanity check "HH:MM"
        try:
            hour_str, minute_str = v.split(":")
            hour = int(hour_str)
            minute = int(minute_str)
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError
        except Exception:
            raise ValueError("time_of_day must be in HH:MM format")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: Optional[List[int]]) -> Optional[List[int]]:
        if v is None:
            return v
        for d in v:
            if d < 0 or d > 6:
                raise ValueError("days_of_week entries must be between 0 and 6")
        return v


class ReminderCreate(ReminderBase):
    pass


class ReminderUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    schedule_kind: Optional[str] = None
    time_of_day: Optional[str] = None
    days_of_week: Optional[List[int]] = None
    one_off_at: Optional[datetime] = None
    grace_before_min: Optional[int] = None
    grace_after_min: Optional[int] = None
    channels: Optional[List[str]] = None
    enabled: Optional[bool] = None


class ReminderOut(ReminderBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OccurrenceOut(BaseModel):
    id: int
    reminder_id: int
    label: str
    due_at: datetime
    state: str

    class Config:
        from_attributes = True


# ---------- Helper functions ----------

def _parse_time_str(t: str) -> time_type:
    hour_str, minute_str = t.split(":")
    return time_type(hour=int(hour_str), minute=int(minute_str))


def _days_to_str(days: Optional[List[int]]) -> Optional[str]:
    if days is None:
        return None
    return ",".join(str(d) for d in sorted(set(days)))


def _str_to_days(s: Optional[str]) -> Optional[List[int]]:
    if not s:
        return None
    return [int(part) for part in s.split(",")]


def _channels_to_str(channels: Optional[List[str]]) -> Optional[str]:
    if channels is None:
        return None
    return ",".join(sorted(set(channels)))


def _str_to_channels(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return s.split(",")


# ---------- CRUD endpoints ----------


@router.get("", response_model=List[ReminderOut])
def list_reminders(db: Session = Depends(get_db)):
    reminders = db.query(Reminder).all()
    # adapt DB fields to API schema
    out: List[ReminderOut] = []
    for r in reminders:
        out.append(
            ReminderOut(
                id=r.id,
                label=r.label,
                description=r.description,
                schedule_kind=r.schedule_kind,
                time_of_day=r.time_of_day.strftime("%H:%M"),
                days_of_week=_str_to_days(r.days_of_week),
                one_off_at=r.one_off_at,
                grace_before_min=r.grace_before_min,
                grace_after_min=r.grace_after_min,
                channels=_str_to_channels(r.channels),
                enabled=r.enabled,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )
    return out


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder(payload: ReminderCreate, db: Session = Depends(get_db)):
    t = _parse_time_str(payload.time_of_day)

    r = Reminder(
        label=payload.label,
        description=payload.description,
        schedule_kind=payload.schedule_kind,
        time_of_day=t,
        days_of_week=_days_to_str(payload.days_of_week),
        one_off_at=payload.one_off_at,
        grace_before_min=payload.grace_before_min,
        grace_after_min=payload.grace_after_min,
        channels=_channels_to_str(payload.channels),
        enabled=payload.enabled,
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    return ReminderOut(
        id=r.id,
        label=r.label,
        description=r.description,
        schedule_kind=r.schedule_kind,
        time_of_day=r.time_of_day.strftime("%H:%M"),
        days_of_week=_str_to_days(r.days_of_week),
        one_off_at=r.one_off_at,
        grace_before_min=r.grace_before_min,
        grace_after_min=r.grace_after_min,
        channels=_str_to_channels(r.channels),
        enabled=r.enabled,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.get("/{reminder_id}", response_model=ReminderOut)
def get_reminder(reminder_id: int, db: Session = Depends(get_db)):
    r = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")

    return ReminderOut(
        id=r.id,
        label=r.label,
        description=r.description,
        schedule_kind=r.schedule_kind,
        time_of_day=r.time_of_day.strftime("%H:%M"),
        days_of_week=_str_to_days(r.days_of_week),
        one_off_at=r.one_off_at,
        grace_before_min=r.grace_before_min,
        grace_after_min=r.grace_after_min,
        channels=_str_to_channels(r.channels),
        enabled=r.enabled,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.patch("/{reminder_id}", response_model=ReminderOut)
def update_reminder(
    reminder_id: int,
    payload: ReminderUpdate,
    db: Session = Depends(get_db),
):
    r = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")

    data = payload.dict(exclude_unset=True)

    if "label" in data:
        r.label = data["label"]
    if "description" in data:
        r.description = data["description"]
    if "schedule_kind" in data:
        r.schedule_kind = data["schedule_kind"].upper()
    if "time_of_day" in data:
        r.time_of_day = _parse_time_str(data["time_of_day"])
    if "days_of_week" in data:
        r.days_of_week = _days_to_str(data["days_of_week"])
    if "one_off_at" in data:
        r.one_off_at = data["one_off_at"]
    if "grace_before_min" in data:
        r.grace_before_min = data["grace_before_min"]
    if "grace_after_min" in data:
        r.grace_after_min = data["grace_after_min"]
    if "channels" in data:
        r.channels = _channels_to_str(data["channels"])
    if "enabled" in data:
        r.enabled = data["enabled"]

    r.updated_at = datetime.utcnow()

    db.add(r)
    db.commit()
    db.refresh(r)

    return ReminderOut(
        id=r.id,
        label=r.label,
        description=r.description,
        schedule_kind=r.schedule_kind,
        time_of_day=r.time_of_day.strftime("%H:%M"),
        days_of_week=_str_to_days(r.days_of_week),
        one_off_at=r.one_off_at,
        grace_before_min=r.grace_before_min,
        grace_after_min=r.grace_after_min,
        channels=_str_to_channels(r.channels),
        enabled=r.enabled,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(reminder_id: int, db: Session = Depends(get_db)):
    r = db.query(Reminder).filter(Reminder.id == reminder_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reminder not found")

    db.delete(r)
    db.commit()
    return
