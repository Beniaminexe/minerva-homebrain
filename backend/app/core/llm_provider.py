from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Dict


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    raw: Any | None = None


class LLMProvider(ABC):
    """Abstract base class for any LLM backend (local or remote)."""

    @abstractmethod
    async def chat(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        ...


class DummyLLMProvider(LLMProvider):
    """Placeholder provider used during early development."""

    async def chat(
        self,
        messages: List[LLMMessage],
        tools: List[Dict[str, Any]] | None = None,
        tool_choice: str = "auto",
    ) -> LLMResponse:
        last_user = next(
            (m.content for m in reversed(messages) if m.role == "user"),
            "",
        )
        content = (
            "Minerva dummy LLM here.\n"
            "You said: " + last_user + "\n\n"
            "LLM integration is not wired up yet."
        )
        return LLMResponse(content=content, raw=None)
