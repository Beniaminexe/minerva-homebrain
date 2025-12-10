from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import (
    Reminder,
    ReminderOccurrence,
    Service,
    Word,
)
from .database import SessionLocal


# --------- Tool schemas (for LLM function-calling later) ---------


def get_tools_schema() -> List[Dict[str, Any]]:
    """
    Return a list of tool definitions in a function-calling style schema.
    This is designed to be fed to an LLM provider in Phase 3.
    """
    return [
        {
            "name": "get_status_today",
            "description": "Get today's overview: word of the day, reminder summary, and service status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "ISO date YYYY-MM-DD. Defaults to today if omitted.",
                    }
                },
                "required": [],
            },
        },
        {
            "name": "list_reminders",
            "description": "List all reminders and their schedules.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "create_reminder",
            "description": "Create a new reminder with a schedule.",
            "parameters": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "description": {"type": "string"},
                    "schedule_kind": {
                        "type": "string",
                        "enum": ["DAILY", "WEEKLY", "ONE_OFF"],
                    },
                    "time_of_day": {
                        "type": "string",
                        "description": "Time in HH:MM format (24h).",
                    },
                    "days_of_week": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0, "maximum": 6},
                        "description": "For WEEKLY reminders: 0=Monday..6=Sunday.",
                    },
                },
                "required": ["label", "schedule_kind", "time_of_day"],
            },
        },
        {
            "name": "mark_occurrence_done",
            "description": "Mark a reminder occurrence as DONE.",
            "parameters": {
                "type": "object",
                "properties": {
                    "occurrence_id": {"type": "integer"},
                },
                "required": ["occurrence_id"],
            },
        },
        {
            "name": "mark_occurrence_skipped",
            "description": "Mark a reminder occurrence as SKIPPED.",
            "parameters": {
                "type": "object",
                "properties": {
                    "occurrence_id": {"type": "integer"},
                },
                "required": ["occurrence_id"],
            },
        },
        {
            "name": "list_services",
            "description": "List all monitored services and their status.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
        {
            "name": "create_service",
            "description": "Register a new service to monitor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "slug": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": ["HTTP", "TCP"],
                    },
                    "target": {
                        "type": "string",
                        "description": "URL for HTTP or host:port for TCP.",
                    },
                },
                "required": ["name", "slug", "kind", "target"],
            },
        },
    ]
