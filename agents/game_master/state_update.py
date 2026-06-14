"""Structured state extraction — how the narration drives world progression.

After the GM streams its narration, a short non-streaming call asks the model to
report what *changed* this turn as structured JSON: world-flag updates, quest
stage / location / quest-log changes, and party HP/condition deltas. The
orchestrator merges these deterministically. This is the production-grade way to
let an LLM narrator move authoritative game state without it inventing the numbers
mid-prose. The mock returns an empty delta, so the pipeline still runs offline.

Quest stages are anchored to documented world_flags (see knowledge/quests.md):
  sigil_read → stage 2 · gate_open → stage 3 · shard_taken → stage 4 · ending set → done
"""
from __future__ import annotations

import json
from typing import Optional

from shared.interfaces.llm import LLMClient, LLMMessage
from shared.state_schema import CampaignState

_UPDATE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "location": {"type": ["string", "null"]},
        "quest_log_add": {"type": ["string", "null"]},
        "world_flags_set": {
            "type": "object",
            "additionalProperties": {"type": ["string", "boolean", "integer"]},
        },
        "party_damage": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "agent": {"type": "string"},
                    "hp_delta": {"type": "integer"},
                    "add_condition": {"type": ["string", "null"]},
                    "remove_condition": {"type": ["string", "null"]},
                },
                "required": ["agent", "hp_delta", "add_condition", "remove_condition"],
            },
        },
    },
    "required": ["location", "quest_log_add", "world_flags_set", "party_damage"],
}

# Flags that gate quest-stage advancement, in order.
_STAGE_FLAGS = [(1, "sigil_read"), (2, "gate_open"), (3, "shard_taken")]


async def extract_state_update(
    narration: str, state: CampaignState, llm: LLMClient, model: str
) -> Optional[dict]:
    messages: list[LLMMessage] = [
        {
            "role": "system",
            "content": (
                "You are the game's bookkeeper. Given the narration of the turn just played, "
                "report ONLY concrete state changes as JSON matching the given schema. Use null / "
                "empty when nothing changed. Valid world flags include: sigil_read, gate_open, "
                "shard_taken, hedeby_shard, yrsa_trust, court_pact, rival_present, kael_trust_level, "
                "ending. hp_delta is negative for damage, positive for healing. Do not invent events "
                "the narration did not describe."
            ),
        },
        {"role": "user", "content": f"CURRENT LOCATION: {state.location}\nNARRATION:\n{narration[-2000:]}"},
    ]
    try:
        raw = await llm.complete(messages, model=model, json_schema=_UPDATE_SCHEMA, temperature=0.2, max_tokens=300)
        return json.loads(raw)
    except Exception:
        return None


def apply_state_update(state: CampaignState, update: Optional[dict]) -> None:
    if not update:
        _advance_quest_stage(state)
        return
    if update.get("location"):
        state.location = update["location"]
    if update.get("quest_log_add"):
        entry = update["quest_log_add"].strip()
        if entry and entry not in state.quest_log:
            state.quest_log.append(entry)
    for k, v in (update.get("world_flags_set") or {}).items():
        state.world_flags[k] = v
    for dmg in update.get("party_damage") or []:
        member = next((c for c in state.party if c.agent == dmg.get("agent")), None)
        if not member:
            continue
        member.health = max(0, min(member.max_health, member.health + int(dmg.get("hp_delta", 0))))
        if dmg.get("add_condition") and dmg["add_condition"] not in member.conditions:
            member.conditions.append(dmg["add_condition"])
        if dmg.get("remove_condition") and dmg["remove_condition"] in member.conditions:
            member.conditions.remove(dmg["remove_condition"])
    _advance_quest_stage(state)


def _advance_quest_stage(state: CampaignState) -> None:
    """Move the quest stage forward based on the flags now set. Stage only advances."""
    stage = state.quest_stage
    for next_stage, flag in [(2, "sigil_read"), (3, "gate_open"), (4, "shard_taken")]:
        if state.world_flags.get(flag) and stage < next_stage:
            stage = next_stage
    state.quest_stage = stage
    if state.world_flags.get("ending"):
        state.active_quest = "The Reckoning — complete"
