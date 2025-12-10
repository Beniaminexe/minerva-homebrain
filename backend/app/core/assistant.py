from __future__ import annotations

from typing import Any, Dict, List, Optional

from .llm_provider import DummyLLMProvider, LLMMessage
from .assistant_tools import get_tools_schema

# For now we keep a simple global provider.
provider = DummyLLMProvider()


async def run_assistant_chat(
    message: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Simple orchestrator for the assistant.
    For Phase 2, this just calls DummyLLMProvider without real tool-calls,
    but the tool schema is prepared and ready for Phase 3.
    """
    system_prompt = (
        "You are Minerva, a homelab assistant. "
        "You help the user with their reminders, services, and status overview. "
        "You MUST NOT invent reminder schedules or service states; "
        "those come from tools provided to you. "
        "Right now, tools may not be wired; answer based on the user's question "
        "and what you are told here."
    )

    messages: List[LLMMessage] = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=message),
    ]

    tools = get_tools_schema()

    # Dummy provider ignores tools for now, but in Phase 3
    # a real provider will use them for function-calling.
    resp = await provider.chat(messages, tools=tools, tool_choice="auto")

    return {
        "reply": resp.content,
        "used_tools": [],  # will be filled in once we add real tool-calls
    }
