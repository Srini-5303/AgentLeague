"""GM narrator synthesis — streams second-person narration from the turn's inputs.

Receives lore (may include GM-only context to inform, never to reveal), the
character agents' speech/actions, resolved roll results, and current state, and
streams narration tokens. The full text is accumulated by the caller for history.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import AsyncIterator

from shared.interfaces.knowledge import LoreChunk
from shared.interfaces.llm import LLMClient, LLMMessage
from shared.state_schema import AgentResponse, CampaignState, RollResult

_GM_PROMPT = Path(__file__).resolve().parent / "system_prompt.md"


@lru_cache(maxsize=1)
def _gm_system() -> str:
    return _GM_PROMPT.read_text(encoding="utf-8")


def _format_inputs(
    player_input: str,
    state: CampaignState,
    lore: list[LoreChunk],
    responses: list[AgentResponse],
    rolls: list[RollResult],
) -> str:
    lines: list[str] = []
    lines.append(f"PLAYER ACTION: {player_input}")
    lines.append(f"LOCATION: {state.location} | QUEST: {state.active_quest} (stage {state.quest_stage}) | TURN: {state.turn + 1}")
    if state.recent_history:
        lines.append("RECENT HISTORY:\n- " + "\n- ".join(state.recent_history[-5:]))
    if lore:
        lines.append("RELEVANT LORE (for your knowledge; reveal only what the player could plausibly learn, NEVER GM-only secrets):")
        for c in lore:
            tag = " [GM-ONLY — DO NOT REVEAL]" if c.gm_only else ""
            lines.append(f"  • {c.title}{tag}: {c.text[:400]}")
    lines.append("PARTY SAID/DID THIS TURN:")
    for r in responses:
        if r.degraded:
            lines.append(f"  • {r.agent}: (silent / holding back)")
        else:
            lines.append(f"  • {r.agent}: \"{r.speech}\" — {r.action} (mood: {r.emotional_state})")
    if rolls:
        lines.append("DICE OUTCOMES (these are LAW — narrate them, do not change them):")
        for roll in rolls:
            lines.append(f"  • {roll.actor} {roll.check}: rolled {roll.roll}+mod = {roll.total} vs DC {roll.difficulty} → {roll.result.upper()}")
    return "\n".join(lines)


async def stream_synthesis(
    player_input: str,
    state: CampaignState,
    lore: list[LoreChunk],
    responses: list[AgentResponse],
    rolls: list[RollResult],
    llm: LLMClient,
    model: str,
) -> AsyncIterator[str]:
    messages: list[LLMMessage] = [
        {"role": "system", "content": _gm_system()},
        {"role": "user", "content": _format_inputs(player_input, state, lore, responses, rolls)},
    ]
    async for token in llm.stream(messages, model=model, temperature=0.9, max_tokens=700):
        yield token
