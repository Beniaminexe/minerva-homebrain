from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models import Reminder, ReminderOccurrence, TelegramChat
from .database import SessionLocal, engine
from .notifications import emit_notification


def _parse_days_of_week(days_str: Optional[str]) -> list[int]:
    if not days_str:
        return []
    return [int(x) for x in days_str.split(",") if x.strip() != ""]


def reminder_should_fire_on(reminder: Reminder, target_date: date) -> bool:
    """Return True if this reminder should produce an occurrence on target_date."""
    if not reminder.enabled:
        return False

    kind = (reminder.schedule_kind or "").upper()

    if kind == "DAILY":
        return True

    if kind == "WEEKLY":
        days = _parse_days_of_week(reminder.days_of_week)
        return target_date.weekday() in days

    if kind == "ONE_OFF":
        if reminder.one_off_at is None:
            return False
        return reminder.one_off_at.date() == target_date

    # Unknown kind
    return False


def ensure_occurrences_for_date(db: Session, target_date: date) -> int:
    """
    For each enabled reminder, ensure there's an occurrence for target_date
    if the schedule says it should fire.
    Returns the number of occurrences created.
    """
    created = 0

    start = datetime.combine(target_date, time.min)
    end = datetime.combine(target_date, time.max)

    reminders = db.query(Reminder).all()

    for r in reminders:
        if not reminder_should_fire_on(r, target_date):
            continue
        if not r.id:
            print("[reminder_engine] skipping reminder without id")
            continue

        # Does an occurrence already exist for this reminder on this date?
        existing = (
            db.query(ReminderOccurrence)
            .filter(
                ReminderOccurrence.reminder_id == r.id,
                ReminderOccurrence.due_at >= start,
                ReminderOccurrence.due_at <= end,
            )
            .first()
        )
        if existing:
            continue

        if kind == "ONE_OFF" and r.one_off_at:
            due_at = r.one_off_at
        else:
            due_at = datetime.combine(target_date, r.time_of_day)

        window_start = due_at - timedelta(minutes=r.grace_before_min or 0)
        window_end = due_at + timedelta(minutes=r.grace_after_min or 0)

        occ = ReminderOccurrence(
            reminder_id=r.id,
            due_at=due_at,
            window_start_at=window_start,
            window_end_at=window_end,
            state="PENDING",
        )
        db.add(occ)
        created += 1

    if created:
        db.commit()

    return created


# ---------- Background scheduler ----------


def ensure_schema_compatibility() -> None:
    """
    Lightweight migration to ensure required columns exist (SQLite).
    """
    with engine.begin() as conn:
        cols = {
            row[1]
            for row in conn.execute(text("PRAGMA table_info(reminder_occurrences)"))
        }
        if "alerted_at" not in cols:
            conn.execute(text("ALTER TABLE reminder_occurrences ADD COLUMN alerted_at DATETIME"))


async def occurrence_scheduler_loop(interval_seconds: int = 60) -> None:
    """
    Background loop that periodically ensures today's occurrences exist.
    """
    while True:
        db = SessionLocal()
        try:
            today = date.today()
            ensure_occurrences_for_date(db, today)

            now = datetime.utcnow()

            # Mark overdue pending occurrences as missed
            missed_occ = db.query(ReminderOccurrence).filter(
                ReminderOccurrence.state == "PENDING",
                ReminderOccurrence.window_end_at.is_not(None),
                ReminderOccurrence.window_end_at < now,
            ).all()
            for occ in missed_occ:
                occ.state = "MISSED"
                occ.updated_at = now
            if missed_occ:
                db.commit()

            # Notify due occurrences (once per occurrence)
            chats = db.query(TelegramChat).filter(TelegramChat.enabled == True).all()
            due_occ = db.query(ReminderOccurrence).filter(
                ReminderOccurrence.state == "PENDING",
                ReminderOccurrence.due_at <= now,
                ReminderOccurrence.alerted_at.is_(None),
            ).all()

            for occ in due_occ:
                label = occ.reminder.label if occ.reminder else "Reminder"
                text = f"⏰ Reminder: {label} ({occ.due_at.strftime('%H:%M')})"
                due_at_iso = occ.due_at.isoformat()

                for chat in chats:
                    await emit_notification(
                        {
                            "channel": "telegram",
                            "chat_id": chat.chat_id,
                            "text": text,
                            "occurrence_id": occ.id,
                            "label": label,
                            "due_at": due_at_iso,
                        }
                    )
                occ.alerted_at = now
                occ.updated_at = now
            if due_occ:
                db.commit()
        finally:
            db.close()

        await asyncio.sleep(interval_seconds)
