from datetime import datetime, date
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Minerva Home Brain", version="0.1.0")


class StatusTodayResponse(BaseModel):
    now: datetime
    services: list
    word_of_day: dict
    reminders_summary: dict
    expression: dict


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    meta: dict


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat() + "Z"}


@app.get("/status/today", response_model=StatusTodayResponse)
def status_today():
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


@app.post("/assistant/chat", response_model=ChatResponse)
def assistant_chat(payload: ChatRequest):
    session_id = payload.session_id or "session-1"
    reply = (
        "Minerva is online but still initializing.\n"
        "Right now I only know about /status/today and /health."
    )
    return ChatResponse(
        session_id=session_id,
        reply=reply,
        meta={"used_tools": [], "mode": "stub"},
    )
