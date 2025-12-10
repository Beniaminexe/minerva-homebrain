from datetime import datetime, date, time, timedelta

from sqlalchemy.orm import Session

from ..models import Reminder, ReminderOccurrence, Service, ServiceStatus, Word



def seed_initial_data(db: Session) -> None:
    """Seed minimal data if tables are empty."""
    # Seed a word
    if db.query(Word).count() == 0:
        w = Word(
            word="serendipity",
            definition="The occurrence of events by chance in a happy or beneficial way.",
            extra_json='{"examples": ["Finding Minerva bugs before they happen."]}',
            active=True,
        )
        db.add(w)

    # Seed a service
    if db.query(Service).count() == 0:
        s = Service(
            name="Cartofia site",
            slug="cartofia",
            kind="HTTP",
            target="https://cartofia.com",
            check_interval_sec=60,
            timeout_sec=5,
            enabled=True,
        )
        db.add(s)
        db.flush()  # so s.id is available

        status = ServiceStatus(
            service_id=s.id,
            is_up=True,
            latency_ms=123.0,
            last_checked_at=datetime.utcnow(),
            consecutive_failures=0,
            last_change_at=datetime.utcnow(),
        )
        db.add(status)

    # Seed a reminder + today's occurrence
    if db.query(Reminder).count() == 0:
        r = Reminder(
            label="Morning pills",
            description="Take your morning meds.",
            schedule_kind="DAILY",
            time_of_day=time(hour=9, minute=0),
            days_of_week=None,
            grace_before_min=0,
            grace_after_min=60,
            channels="telegram,esp32",
            enabled=True,
        )
        db.add(r)
        db.flush()

        today = date.today()
        due_at = datetime.combine(today, r.time_of_day)
        window_start = due_at  # no early window yet
        window_end = due_at + timedelta(minutes=r.grace_after_min)

        occ = ReminderOccurrence(
            reminder_id=r.id,
            due_at=due_at,
            window_start_at=window_start,
            window_end_at=window_end,
            state="PENDING",
        )
        db.add(occ)

    db.commit()
