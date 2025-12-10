from datetime import datetime, date
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["status"])


class StatusTodayResponse(BaseModel):
    now: datetime
    services: list
    word_of_day: dict
    reminders_summary: dict
    expression: dict


@router.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@router.get("/status/today", response_model=StatusTodayResponse)
def status_today():
    # Stubbed for now. Phase 2 will plug in real logic + DB.
    now = datetime.utcnow()
    return StatusTodayResponse(
        now=now,
        services=[],
        word_of_day={
            "word": "placeholder",
            "definition": "Minerva is waking up.",
            "extra": {},
        },
        reminders_summary={
            "date": date.today().isoformat(),
            "total": 0,
            "done": 0,
            "pending": 0,
            "missed": 0,
            "next": None,
        },
        expression={
            "state": "idle",
            "message": "Booting Minerva...",
        },
    )
