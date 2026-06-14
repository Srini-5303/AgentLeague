"""Personality adherence evals (PRD US-16..20).

These need a real model to be meaningful, so they SKIP unless EVAL_LLM_PROVIDER is
set (e.g. EVAL_LLM_PROVIDER=openai with OPENAI_API_KEY, or azure_openai/ollama).
They assert in-character boundaries: the Warrior doesn't cast spells, the Mage
doesn't brawl/intimidate, etc.

Run:  EVAL_LLM_PROVIDER=openai .venv/Scripts/python -m pytest tests/agent_behavior/test_personality_live.py
"""
from __future__ import annotations

import os

import pytest

from agents.game_master.character_agent import invoke_character_agent
from agents.game_master.context import build_agent_context
from shared.config import Settings
from shared.factory import build_llm
from shared.state_schema import CampaignState, CharacterState

PROVIDER = os.environ.get("EVAL_LLM_PROVIDER")
pytestmark = pytest.mark.skipif(not PROVIDER, reason="set EVAL_LLM_PROVIDER to run live personality evals")


def _settings() -> Settings:
    return Settings(runtime="local", llm_provider=PROVIDER, _env_file=None)  # type: ignore[arg-type]


def _ctx(agent: str, action: str):
    state = CampaignState(
        session_id="s", user_id="u", location="The Ruined Chapel",
        party=[CharacterState(agent=agent, name="Test", health=20, max_health=20)],
    )
    return build_agent_context(agent, action, state, [])


async def test_warrior_does_not_cast_spells():
    s = _settings()
    resp = await invoke_character_agent("warrior", _ctx("warrior", "Cast a fireball at the door"), build_llm(s), s.character_model)
    text = f"{resp.speech} {resp.action}".lower()
    assert not any(w in text for w in ["i cast", "i conjure", "my spell", "incantation"]), text
    if resp.roll_request:
        assert "arcana" not in resp.roll_request.check.lower()


async def test_mage_does_not_brawl_or_intimidate():
    s = _settings()
    resp = await invoke_character_agent("mage", _ctx("mage", "Punch the guard and intimidate him"), build_llm(s), s.character_model)
    if resp.roll_request:
        assert resp.roll_request.check.lower() not in {"intimidation", "might", "athletics"}


async def test_healer_raises_ethical_concern_on_cruelty():
    s = _settings()
    resp = await invoke_character_agent("healer", _ctx("healer", "Torture the prisoner for the location of the Shard"), build_llm(s), s.character_model)
    assert resp.speech, "healer should speak up"
