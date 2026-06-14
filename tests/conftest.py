"""Shared test fixtures. All tests run against the mock LLM + a temp SQLite DB —
no network, no keys, fully deterministic."""
from __future__ import annotations

import pytest

from agents.game_master.orchestrator import GameMaster
from shared.config import Settings
from shared.factory import build_auth, build_knowledge, build_llm, build_state
from shared.state_schema import TurnRequest


def make_settings(tmp_path, **overrides) -> Settings:
    base = dict(
        runtime="local",
        llm_provider="mock",
        sqlite_path=str(tmp_path / "test.db"),
        knowledge_dir="knowledge",
        dice_seed=7,
        dev_auth_bypass=True,
        _env_file=None,  # ignore the project .env so tests are hermetic
    )
    base.update(overrides)
    return Settings(**base)


def make_gm(settings: Settings) -> GameMaster:
    return GameMaster(
        llm=build_llm(settings),
        knowledge=build_knowledge(settings),
        state=build_state(settings),
        auth=build_auth(settings),
        settings=settings,
    )


@pytest.fixture
def gm(tmp_path):
    return make_gm(make_settings(tmp_path))


async def collect(agen) -> list[dict]:
    return [ev async for ev in agen]


async def run_turn(gm: GameMaster, text: str, token: str | None = None, confirm_token: str | None = None) -> list[dict]:
    return await collect(gm.run_turn(token, TurnRequest(input=text, confirm_token=confirm_token)))
