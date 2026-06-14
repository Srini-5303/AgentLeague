"""Generate 3–4 player choices at the end of a turn (PRD US-06).

A short, non-streaming LLM call given the narration just produced. Falls back to
sensible generic options if the model misbehaves — the turn must always end with
actionable choices.
"""
from __future__ import annotations

import json

from shared.interfaces.llm import LLMClient, LLMMessage

_CHOICES_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    # Note: OpenAI/Azure strict structured-output mode rejects minItems/maxItems,
    # so we bound the count in code (below) rather than the schema.
    "properties": {
        "choices": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["choices"],
}

_FALLBACK = ["Press onward", "Search the area", "Confer with the party", "Hold and wait"]


async def generate_choices(narration: str, llm: LLMClient, model: str) -> list[str]:
    messages: list[LLMMessage] = [
        {
            "role": "system",
            "content": (
                "You suggest 3 or 4 short, distinct next actions a player could take, in second "
                "person, each under 8 words, grounded in the scene just narrated. Norse fantasy tone. "
                'Respond ONLY as JSON: {"choices": ["...", "..."]}.'
            ),
        },
        {"role": "user", "content": f"SCENE:\n{narration[-1500:]}"},
    ]
    try:
        raw = await llm.complete(messages, model=model, json_schema=_CHOICES_SCHEMA, temperature=0.7, max_tokens=200)
        choices = json.loads(raw).get("choices") or []
        choices = [c.strip() for c in choices if c.strip()][:4]
        return choices if len(choices) >= 3 else _FALLBACK
    except Exception:
        return _FALLBACK
