"""Turn context construction and agent selection.

- select_agents(): decide which 1..N character agents to invoke this turn. Local
  implementation is rules-based (deterministic, cheap, testable); in Azure this
  could be swapped for a small classifier prompt. Capped by MAX_AGENTS_PER_TURN.
- build_agent_context(): the structured context object the GM hands each character
  agent. GM-only lore is NEVER placed here.
"""
from __future__ import annotations

from shared.config import get_settings
from shared.interfaces.knowledge import LoreChunk
from shared.state_schema import CampaignState

ALL_AGENTS = ["warrior", "mage", "rogue", "healer", "rival"]

# Keyword → agent affinities for cheap, deterministic local selection.
_AFFINITY = {
    "warrior": ["fight", "attack", "guard", "shield", "charge", "defend", "battle", "enemy", "door", "force"],
    "mage": ["rune", "magic", "sigil", "arcane", "spell", "moon", "ritual", "ancient", "glow", "seidr", "seiðr"],
    "rogue": ["sneak", "hide", "lock", "trap", "steal", "scout", "shadow", "pick", "guard", "quiet", "spy"],
    "healer": ["heal", "wound", "hurt", "pray", "rest", "sick", "dead", "spirit", "help", "save", "comfort"],
    "rival": ["kael", "thorn", "rival", "betray", "bargain", "deal", "challenge", "duel"],
}


def select_agents(player_input: str, state: CampaignState) -> list[str]:
    text = player_input.lower()
    scores: dict[str, int] = {}
    for agent, words in _AFFINITY.items():
        hit = sum(1 for w in words if w in text)
        if hit:
            scores[agent] = hit
    # Rival appears only when explicitly invoked or already present in the scene.
    if "rival" in scores and not (state.world_flags.get("rival_present") or "kael" in text):
        scores.pop("rival", None)
    chosen = [a for a, _ in sorted(scores.items(), key=lambda kv: kv[1], reverse=True)]
    if not chosen:
        # Default party voices when intent is ambiguous: the protector and the scholar.
        chosen = ["warrior", "mage"]
    cap = get_settings().max_agents_per_turn
    return chosen[:cap]


def build_agent_context(
    agent: str,
    player_input: str,
    state: CampaignState,
    lore: list[LoreChunk],
) -> dict:
    """Player-safe context for a single character agent. No GM-only secrets."""
    party = [
        {"name": c.name, "agent": c.agent, "health": f"{c.health}/{c.max_health}",
         "conditions": c.conditions}
        for c in state.party
    ]
    return {
        "you_are": agent,
        "scene": {
            "location": state.location,
            "active_quest": state.active_quest,
            "quest_stage": state.quest_stage,
            "turn": state.turn + 1,
        },
        "recent_history": state.recent_history[-5:],
        "party": party,
        "player_action": player_input,
        "relevant_lore": [{"title": c.title, "text": c.text} for c in lore],
    }
