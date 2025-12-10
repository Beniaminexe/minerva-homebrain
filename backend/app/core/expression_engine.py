from datetime import datetime, time
from typing import List, Optional


class Expression:
    def __init__(self, state: str, message: str):
        self.state = state
        self.message = message


def compute_expression(
    now: datetime,
    *,
    pending_count: int,
    missed_count: int,
    any_service_down: bool,
    failing_services: Optional[List[str]] = None,
    upcoming_next_label: Optional[str] = None,
) -> Expression:
    """
    Determines Minerva's emotional state based on reminders + services.
    """

    hour = now.hour

    # ---------- Night mode ----------
    if 1 <= hour <= 5:
        # Only warn if something is *really* wrong
        if any_service_down:
            msg = (
                f"{failing_services[0]} down (night alert)"
                if failing_services else "Service down (night alert)"
            )
            return Expression("alert", msg)
        return Expression("sleepy", "Quiet hours...")

    # ---------- Service outages dominate ----------
    if any_service_down:
        msg = (
            f"{failing_services[0]} down!"
            if failing_services else "A service is down!"
        )
        return Expression("warning", msg)

    # ---------- Reminders logic ----------
    if missed_count > 0:
        return Expression("alert", "You missed some reminders.")

    if pending_count > 0:
        # Focused mode when working through tasks
        if upcoming_next_label:
            return Expression("focused", f"Next: {upcoming_next_label}")
        return Expression("focused", "You have pending reminders.")

    # ---------- All clear ----------
    return Expression("happy", "All good!")
