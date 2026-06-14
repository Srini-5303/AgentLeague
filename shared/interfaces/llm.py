from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, TypedDict


class LLMMessage(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMClient(ABC):
    """Provider-agnostic chat interface used by character agents and the narrator."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        json_schema: Optional[dict] = None,
        temperature: float = 0.8,
        max_tokens: int = 600,
    ) -> str:
        """Return a full completion. If json_schema is given, the result must be
        valid JSON conforming to it (provider enforces where possible)."""

    @abstractmethod
    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        """Yield text deltas (tokens) as they arrive."""
