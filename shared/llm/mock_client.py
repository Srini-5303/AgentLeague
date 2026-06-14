"""Deterministic, network-free LLM used for tests and offline dev.

It inspects the system prompt to figure out which agent is speaking and returns
plausible in-character structured JSON (or narration for the narrator), so the
full turn pipeline can be exercised without any model or key.
"""
from __future__ import annotations

import json
import re
from typing import AsyncIterator, Optional

from shared.interfaces.llm import LLMClient, LLMMessage

# Canned in-character lines keyed by agent slug found in the system prompt.
_AGENT_LINES = {
    "warrior": ("I'll take point — shields up.", "raises his shield and advances", "Might"),
    "mage": ("These runes are older than the shatter.", "studies the carvings", "Arcana"),
    "rogue": ("Give me thirty seconds with the lock.", "slips into the shadows", "Stealth"),
    "healer": ("Tread carefully — the dead remember.", "whispers a warding prayer", "Insight"),
    "rival": ("You're slower than I'd hoped.", "smirks and keeps his blade loose", "Persuasion"),
}


def _detect_agent(messages: list[LLMMessage]) -> Optional[str]:
    # Prefer the explicit "you_are" marker in the user context (unambiguous);
    # fall back to scanning the system prompt.
    for m in messages:
        if m["role"] == "user":
            for slug in _AGENT_LINES:
                if f'"you_are": "{slug}"' in m["content"] or f'"you_are":"{slug}"' in m["content"]:
                    return slug
    sys = " ".join(m["content"].lower() for m in messages if m["role"] == "system")
    for slug in _AGENT_LINES:
        if f"**{slug}**" in sys:
            return slug
    return None


class MockLLMClient(LLMClient):
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        json_schema: Optional[dict] = None,
        temperature: float = 0.8,
        max_tokens: int = 600,
    ) -> str:
        agent = _detect_agent(messages)
        if json_schema and agent:
            speech, action, check = _AGENT_LINES[agent]
            payload = {
                "agent": agent,
                "speech": speech,
                "action": action,
                "roll_request": {
                    "actor": agent,
                    "check": check,
                    "modifier": 2,
                    "difficulty": 12,
                    "kind": "check",
                },
                "emotional_state": "resolute",
            }
            return json.dumps(payload)
        if json_schema:
            # e.g. choices generation
            return json.dumps({"choices": ["Press on", "Search the chapel", "Ask the party", "Retreat"]})
        # Plain text (narrator synthesis / summarization)
        return "The torchlight gutters as the party weighs its next move beneath the broken moon."

    async def stream(
        self,
        messages: list[LLMMessage],
        *,
        model: str,
        temperature: float = 0.8,
        max_tokens: int = 800,
    ) -> AsyncIterator[str]:
        text = (
            "Cold wind threads through the shattered nave. Bran sets his shield, "
            "Lyra traces a rune that pulses with pale moonlight, and somewhere below "
            "the stone, something old stirs. The party's choice will shape what wakes."
        )
        for word in re.findall(r"\S+\s*", text):
            yield word
