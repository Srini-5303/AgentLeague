"""Rolling history summarization to keep long campaigns inside the context window.

recent_history holds short per-turn summaries. Every HISTORY_SUMMARIZE_EVERY turns
the oldest entries are collapsed into a single paragraph by the model, which then
heads the list — so the GM always sees a compact saga-so-far plus the latest turns.
"""
from __future__ import annotations

from shared.interfaces.llm import LLMClient, LLMMessage


async def maybe_summarize(
    recent_history: list[str], turn: int, every: int, llm: LLMClient, model: str
) -> list[str]:
    # Summarize when we have a backlog and we're on the cadence.
    if turn == 0 or turn % every != 0 or len(recent_history) <= 5:
        return recent_history
    older, keep = recent_history[:-5], recent_history[-5:]
    if not older:
        return recent_history
    messages: list[LLMMessage] = [
        {
            "role": "system",
            "content": (
                "Condense these earlier turns of a Norse fantasy campaign into ONE tight paragraph "
                "(<120 words) capturing what matters for continuity: choices made, oaths sworn, foes "
                "faced, places reached. Past tense, saga voice. Prose only."
            ),
        },
        {"role": "user", "content": "\n".join(older)},
    ]
    try:
        paragraph = (await llm.complete(messages, model=model, temperature=0.4, max_tokens=200)).strip()
        return [f"Saga so far: {paragraph}", *keep] if paragraph else recent_history
    except Exception:
        return recent_history
