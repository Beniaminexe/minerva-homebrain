from datetime import datetime, timedelta
import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import NotificationEvent

router = APIRouter(prefix="/notifications", tags=["notifications"])
MAX_ATTEMPTS = 5


class NotificationOut(BaseModel):
    id: int
    channel: str
    payload: dict
    status: str
    attempt_count: int
    last_error: Optional[str]
    locked_at: Optional[datetime]
    locked_by: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FailRequest(BaseModel):
    error_message: str


class AckResponse(BaseModel):
    ok: bool
    id: int
    status: str
    attempt_count: int
    last_error: Optional[str] = None


@router.get("/pending", response_model=List[NotificationOut])
def pending_notifications(
    limit: int = Query(50, ge=1, le=100),
    consumer_id: str = Query("telegram-bot", min_length=1, max_length=128),
    lock_seconds: int = Query(60, ge=1, le=3600),
    db: Session = Depends(get_db),
):
    now = datetime.utcnow()
    lock_threshold = now - timedelta(seconds=lock_seconds)

    # Select candidates eligible for processing
    candidates = (
        db.query(NotificationEvent)
        .filter(
            NotificationEvent.sent_at.is_(None),
            NotificationEvent.attempt_count < MAX_ATTEMPTS,
            NotificationEvent.status.in_(("PENDING", "FAILED")),
            or_(
                NotificationEvent.locked_at.is_(None),
                NotificationEvent.locked_at < lock_threshold,
            ),
        )
        .order_by(NotificationEvent.created_at.asc())
        .limit(limit)
        .all()
    )

    # Claim them
    claimed: List[NotificationEvent] = []
    for evt in candidates:
        evt.locked_at = now
        evt.locked_by = consumer_id
        evt.status = "SENDING"
        evt.updated_at = now
        db.add(evt)
        claimed.append(evt)

    if claimed:
        db.commit()
        for evt in claimed:
            db.refresh(evt)

    result: List[NotificationOut] = []
    for evt in claimed:
        try:
            payload = json.loads(evt.payload_json)
        except Exception:
            payload = {}

        result.append(
            NotificationOut(
                id=evt.id,
                channel=evt.channel,
                payload=payload,
                status=evt.status,
                attempt_count=evt.attempt_count,
                last_error=evt.last_error,
                locked_at=evt.locked_at,
                locked_by=evt.locked_by,
                sent_at=evt.sent_at,
                created_at=evt.created_at,
                updated_at=evt.updated_at,
            )
        )

    return result


@router.post("/{event_id}/ack", response_model=AckResponse)
def ack_notification(event_id: int, db: Session = Depends(get_db)):
    evt = db.query(NotificationEvent).filter(NotificationEvent.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Notification not found")

    now = datetime.utcnow()
    evt.status = "SENT"
    evt.sent_at = now
    evt.acked_at = now
    evt.locked_at = None
    evt.locked_by = None
    evt.updated_at = now
    db.add(evt)
    db.commit()
    db.refresh(evt)

    return AckResponse(
        ok=True,
        id=evt.id,
        status=evt.status,
        attempt_count=evt.attempt_count,
        last_error=evt.last_error,
    )


@router.post("/{event_id}/fail", response_model=AckResponse)
def fail_notification(
    event_id: int,
    payload: FailRequest,
    db: Session = Depends(get_db),
):
    evt = db.query(NotificationEvent).filter(NotificationEvent.id == event_id).first()
    if not evt:
        raise HTTPException(status_code=404, detail="Notification not found")

    evt.attempt_count = (evt.attempt_count or 0) + 1
    evt.last_error = payload.error_message
    evt.status = "FAILED"
    evt.locked_at = None
    evt.locked_by = None
    evt.updated_at = datetime.utcnow()
    db.add(evt)
    db.commit()
    db.refresh(evt)

    return AckResponse(
        ok=True,
        id=evt.id,
        status=evt.status,
        attempt_count=evt.attempt_count,
        last_error=evt.last_error,
    )
