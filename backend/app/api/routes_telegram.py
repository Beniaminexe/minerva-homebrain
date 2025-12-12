from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models import TelegramChat

router = APIRouter(prefix="/integrations/telegram", tags=["telegram"])


class TelegramRegisterRequest(BaseModel):
    chat_id: int
    chat_type: str | None = "private"
    username: str | None = None
    title: str | None = None


class TelegramRegisterResponse(BaseModel):
    ok: bool
    chat_id: int
    enabled: bool


@router.post("/register", response_model=TelegramRegisterResponse)
def register_chat(payload: TelegramRegisterRequest, db: Session = Depends(get_db)):
    chat = db.query(TelegramChat).filter(TelegramChat.chat_id == payload.chat_id).first()

    now = datetime.utcnow()

    if not chat:
        chat = TelegramChat(
            chat_id=payload.chat_id,
            chat_type=payload.chat_type or "private",
            username=payload.username,
            title=payload.title,
            enabled=True,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(chat)
    else:
        chat.chat_type = payload.chat_type or chat.chat_type
        chat.username = payload.username
        chat.title = payload.title
        chat.last_seen_at = now
        # leave enabled as-is

    db.commit()
    db.refresh(chat)

    return TelegramRegisterResponse(ok=True, chat_id=chat.chat_id, enabled=chat.enabled)
