from datetime import datetime, date, time, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.expression_engine import compute_expression
from ..core.database import get_db
from ..models import Service, Word, ReminderOccurrence

router = APIRouter(tags=["status"])


class ServiceItem(BaseModel):
    id: int
    name: str
    slug: str
    is_up: bool
    latency_ms: float | None
    last_checked_at: datetime | None


class WordOfDayItem(BaseModel):
    word: str
    definition: str
    extra: dict | None = None


class NextOccurrenceItem(BaseModel):
    occurrence_id: int
    label: str
    due_at: datetime
    state: str


class RemindersSummary(BaseModel):
    date: str
    total: int
    done: int
    pending: int
    missed: int
    next: NextOccurrenceItem | None


class StatusTodayResponse(BaseModel):
    now: datetime
    services: list[ServiceItem]
    word_of_day: WordOfDayItem
    reminders_summary: RemindersSummary
    expression: dict


@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@router.get("/status/today", response_model=StatusTodayResponse)
def status_today(db: Session = Depends(get_db)):
    now = datetime.utcnow()

    # --- Services ---
    services_db = db.query(Service).all()
    services: list[ServiceItem] = []
    for s in services_db:
        status = s.status
        services.append(
            ServiceItem(
                id=s.id,
                name=s.name,
                slug=s.slug,
                is_up=status.is_up if status else False,
                latency_ms=status.latency_ms if status else None,
                last_checked_at=status.last_checked_at if status else None,
            )
        )

    # --- Word of the day ---
    words = (
        db.query(Word)
        .filter(Word.active == True)  # noqa: E712
        .order_by(Word.id)
        .all()
    )
    if words:
        today = date.today()
        idx = today.toordinal() % len(words)
        w = words[idx]
        extra = None
        if w.extra_json:
            import json

            try:
                extra = json.loads(w.extra_json)
            except Exception:
                extra = None

        word_of_day = WordOfDayItem(
            word=w.word,
            definition=w.definition,
            extra=extra,
        )
    else:
        word_of_day = WordOfDayItem(
            word="placeholder",
            definition="No words configured yet.",
            extra=None,
        )

    # --- Reminders summary (today only) ---
    start = datetime.combine(date.today(), time.min)
    end = datetime.combine(date.today(), time.max)

    occurrences = (
        db.query(ReminderOccurrence)
        .filter(
            ReminderOccurrence.due_at >= start,
            ReminderOccurrence.due_at <= end,
        )
        .all()
    )

    total = len(occurrences)
    done = sum(1 for o in occurrences if o.state == "DONE")
    pending = sum(1 for o in occurrences if o.state == "PENDING")
    missed = sum(1 for o in occurrences if o.state == "MISSED")

    next_occ: NextOccurrenceItem | None = None
    future_pending = [
        o for o in occurrences if o.state == "PENDING" and o.due_at >= now
    ]
    if future_pending:
        nxt = min(future_pending, key=lambda o: o.due_at)
        # lazy join via relationship
        label = nxt.reminder.label if nxt.reminder else "Unknown"
        next_occ = NextOccurrenceItem(
            occurrence_id=nxt.id,
            label=label,
            due_at=nxt.due_at,
            state=nxt.state,
        )

    reminders_summary = RemindersSummary(
        date=date.today().isoformat(),
        total=total,
        done=done,
        pending=pending,
        missed=missed,
        next=next_occ,
    )

        # ---------- Expression engine ----------
    failing_services = [s.name for s in services if not s.is_up]
    any_service_down = len(failing_services) > 0

    next_label = (
        next_occ.label if next_occ else None
    )

    expr = compute_expression(
        now,
        pending_count=pending,
        missed_count=missed,
        any_service_down=any_service_down,
        failing_services=failing_services,
        upcoming_next_label=next_label,
    )

    expression = {"state": expr.state, "message": expr.message}
    
    return StatusTodayResponse(
        now=now,
        services=services,
        word_of_day=word_of_day,
        reminders_summary=reminders_summary,
        expression=expression,
    )


