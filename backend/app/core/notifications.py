from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import NotificationEvent
from .database import SessionLocal, engine

Notification = Dict[str, Any]
NotificationHandler = Callable[[Notification], Awaitable[None]]

_handler: Optional[NotificationHandler] = None


def register_notification_handler(handler: NotificationHandler) -> None:
    """
    Register an async handler to receive notifications.
    Backend remains functional if no handler is registered.
    """
    global _handler
    _handler = handler


async def emit_notification(notification: Notification) -> None:
    """
    Deliver a notification to the registered handler if present,
    and persist it for durable delivery.
    """
    # Persist to database for later consumption
    db: Session = SessionLocal()
    try:
        evt = NotificationEvent(
            channel=notification.get("channel", "default"),
            payload_json=json.dumps(notification),
            status="PENDING",
        )
        db.add(evt)
        db.commit()
    finally:
        db.close()

    # Optional in-process handler hook
    handler = _handler
    if handler:
        try:
            await handler(notification)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[notifications] handler error: {exc}")


def ensure_notification_schema(lock_columns: bool = True) -> None:
    """
    Minimal schema guard for notification_events table (SQLite).
    """
    with engine.begin() as conn:
        cols = {
            row[1] for row in conn.execute(text("PRAGMA table_info(notification_events)"))
        }
        if "locked_at" not in cols and lock_columns:
            conn.execute(text("ALTER TABLE notification_events ADD COLUMN locked_at DATETIME"))
        if "locked_by" not in cols and lock_columns:
            conn.execute(text("ALTER TABLE notification_events ADD COLUMN locked_by VARCHAR"))
        if "sent_at" not in cols:
            conn.execute(text("ALTER TABLE notification_events ADD COLUMN sent_at DATETIME"))
