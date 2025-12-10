from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["assistant"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    meta: dict


@router.post("/assistant/chat", response_model=ChatResponse)
def assistant_chat(payload: ChatRequest):
    # This is a stub. Later we'll call core.llm_provider here.
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
