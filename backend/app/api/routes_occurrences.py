from datetime import date, datetime, time as time_type
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import ReminderOccurrence

router = APIRouter(prefix="/occurrences", tags=["occurrences"])


# ---------- Schemas ----------


class OccurrenceOut(BaseModel):
    id: int
    reminder_id: int
    label: str
    due_at: datetime
    state: str

    class Config:
        from_attributes = True


class OccurrenceStateChangeResponse(BaseModel):
    id: int
    state: str
    done_at: Optional[datetime] = None
    skipped_at: Optional[datetime] = None


# ---------- Helpers ----------


def _parse_date_or_today(date_str: Optional[str]) -> date:
    if not date_str:
        return date.today()
    return datetime.strptime(date_str, "%Y-%m-%d").date()


# ---------- Endpoints ----------


@router.get("", response_model=List[OccurrenceOut])
def list_occurrences(
    date_str: Optional[str] = Query(
        None,
        alias="date",
        description="ISO date YYYY-MM-DD, defaults to today",
    ),
    state: Optional[str] = Query(
        None,
        description="Filter by state: PENDING, DONE, MISSED, SKIPPED",
    ),
    reminder_id: Optional[int] = Query(
        None,
        description="Filter by reminder_id",
    ),
    db: Session = Depends(get_db),
):
    target_date = _parse_date_or_today(date_str)

    start = datetime.combine(target_date, time_type.min)
    end = datetime.combine(target_date, time_type.max)

    q = db.query(ReminderOccurrence).filter(
        ReminderOccurrence.due_at >= start,
        ReminderOccurrence.due_at <= end,
    )

    if state:
        q = q.filter(ReminderOccurrence.state == state.upper())

    if reminder_id:
        q = q.filter(ReminderOccurrence.reminder_id == reminder_id)

    occurrences = q.all()

    result: List[OccurrenceOut] = []
    for o in occurrences:
        label = o.reminder.label if o.reminder else "Unknown"
        result.append(
            OccurrenceOut(
                id=o.id,
                reminder_id=o.reminder_id,
                label=label,
                due_at=o.due_at,
                state=o.state,
            )
        )

    return result


@router.post("/{occurrence_id}/done", response_model=OccurrenceStateChangeResponse)
def mark_occurrence_done(
    occurrence_id: int,
    db: Session = Depends(get_db),
):
    occ = (
        db.query(ReminderOccurrence)
        .filter(ReminderOccurrence.id == occurrence_id)
        .first()
    )
    if not occ:
        raise HTTPException(status_code=404, detail="Occurrence not found")

    if occ.state in ("DONE", "SKIPPED"):
        # idempotent-ish
        return OccurrenceStateChangeResponse(
            id=occ.id,
            state=occ.state,
            done_at=occ.done_at,
            skipped_at=occ.skipped_at,
        )

    now = datetime.utcnow()
    occ.state = "DONE"
    occ.done_at = now
    occ.skipped_at = None
    occ.updated_at = now

    db.add(occ)
    db.commit()
    db.refresh(occ)

    return OccurrenceStateChangeResponse(
        id=occ.id,
        state=occ.state,
        done_at=occ.done_at,
        skipped_at=occ.skipped_at,
    )


@router.post("/{occurrence_id}/skip", response_model=OccurrenceStateChangeResponse)
def mark_occurrence_skipped(
    occurrence_id: int,
    db: Session = Depends(get_db),
):
    occ = (
        db.query(ReminderOccurrence)
        .filter(ReminderOccurrence.id == occurrence_id)
        .first()
    )
    if not occ:
        raise HTTPException(status_code=404, detail="Occurrence not found")

    if occ.state in ("DONE", "SKIPPED"):
        return OccurrenceStateChangeResponse(
            id=occ.id,
            state=occ.state,
            done_at=occ.done_at,
            skipped_at=occ.skipped_at,
        )

    now = datetime.utcnow()
    occ.state = "SKIPPED"
    occ.skipped_at = now
    occ.done_at = None
    occ.updated_at = now

    db.add(occ)
    db.commit()
    db.refresh(occ)

    return OccurrenceStateChangeResponse(
        id=occ.id,
        state=occ.state,
        done_at=occ.done_at,
        skipped_at=occ.skipped_at,
    )
