from fastapi import APIRouter
from pydantic import BaseModel

from ..core.assistant import run_assistant_chat

router = APIRouter(tags=["assistant"])


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    meta: dict


@router.post("/assistant/chat", response_model=ChatResponse)
async def assistant_chat(payload: ChatRequest):
    session_id = payload.session_id or "session-1"

    result = await run_assistant_chat(
        message=payload.message,
        session_id=session_id,
    )

    return ChatResponse(
        session_id=session_id,
        reply=result["reply"],
        meta={"used_tools": result.get("used_tools", []), "mode": "dummy"},
    )
