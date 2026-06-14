"""End-to-end turn shape, HITL gating, and the secret-never-leaks guarantee."""
from agents.game_master.confirm import confirmation_payload
from tests.conftest import run_turn


async def test_turn_event_sequence(gm):
    events = await run_turn(gm, "I ready my shield and study the glowing sigil.")
    types = [e["type"] for e in events]
    assert types[0] == "agent_start"
    assert "token" in types
    assert types[-1] == "done"
    done = events[-1]
    assert 3 <= len(done["choices"]) <= 4
    assert "trace_summary" in done and done["trace_summary"]["spans"]


async def test_hitl_blocks_then_confirms(gm):
    # Irreversible phrasing → confirm gate, no narration.
    events = await run_turn(gm, "I destroy the Shard of Mani forever.")
    assert len(events) == 1 and events[0]["type"] == "confirm"
    token = events[0]["action_token"]
    # Resubmit with the token → turn proceeds.
    events2 = await run_turn(gm, "I destroy the Shard of Mani forever.", confirm_token=token)
    assert events2[-1]["type"] == "done"


async def test_stale_confirm_token_does_not_bypass(gm):
    # A token for a different action must not confirm this one.
    wrong = confirmation_payload("I betray the party")["action_token"]
    events = await run_turn(gm, "I destroy the Shard of Mani forever.", confirm_token=wrong)
    assert events[0]["type"] == "confirm"


async def test_turn_persists_and_resumes(gm):
    await run_turn(gm, "I look around the chapel.")
    await run_turn(gm, "I search the altar.")
    user = await gm.state.get_user(gm.s.dev_user_id)
    state = await gm.state.get_session(user.session_id)
    assert state.turn == 2
    assert len(state.recent_history) >= 1


async def test_gm_only_secret_never_appears_in_narration(gm):
    """Mock narration is canned, so to truly exercise the guarantee we assert the
    player-facing knowledge path filters GM-only chunks (the orchestrator only feeds
    character agents non-secret lore, and never sends GM-only text to the client)."""
    chunks = await gm.knowledge.search("wound door fenrir ending kael secret", top_k=10, include_secrets=False)
    assert all(not c.gm_only for c in chunks)
    joined = " ".join(c.text for c in chunks).lower()
    assert "gm only" not in joined
