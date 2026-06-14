"""Auth + session isolation — PRD's 100% isolation guarantee."""
import pytest

from shared.auth.dev_auth import mint_dev_token
from shared.state_schema import CampaignState, UserRecord
from tests.conftest import make_gm, make_settings, run_turn


@pytest.fixture
def secure_gm(tmp_path):
    # bypass off → real token validation path
    s = make_settings(tmp_path, dev_auth_bypass=False, dev_auth_secret="test-secret")
    return make_gm(s), s


async def test_missing_token_returns_401(secure_gm):
    gm, _ = secure_gm
    events = await run_turn(gm, "I look around", token=None)
    assert events and events[0]["type"] == "error" and events[0]["status"] == 401


async def test_invalid_token_returns_401(secure_gm):
    gm, _ = secure_gm
    events = await run_turn(gm, "I look around", token="Bearer garbage.token.here")
    assert events[0]["type"] == "error" and events[0]["status"] == 401


async def test_two_users_get_distinct_sessions(secure_gm):
    gm, s = secure_gm
    ta = mint_dev_token("userA", s.dev_auth_secret)
    tb = mint_dev_token("userB", s.dev_auth_secret)
    await run_turn(gm, "I begin", token=f"Bearer {ta}")
    await run_turn(gm, "I begin", token=f"Bearer {tb}")
    ua = await gm.state.get_user("userA")
    ub = await gm.state.get_user("userB")
    assert ua.session_id != ub.session_id
    # userA's resolved session is owned by userA only.
    sess_a = await gm.state.get_session(ua.session_id)
    assert sess_a.user_id == "userA"


async def test_ownership_guard_blocks_foreign_session(secure_gm, monkeypatch):
    """If a user record somehow points at a session owned by someone else, the GM
    must refuse with 403 and process nothing."""
    gm, s = secure_gm
    token = mint_dev_token("attacker", s.dev_auth_secret)
    # Plant a victim session and make the attacker's user record point at it.
    victim = CampaignState(session_id="victim-sess", user_id="victim")
    await gm.state.write_session(victim)
    await gm.state.create_user(UserRecord(id="attacker", session_id="victim-sess"))
    events = await run_turn(gm, "I steal the save", token=f"Bearer {token}")
    assert events[0]["type"] == "error" and events[0]["status"] == 403
    # nothing beyond the error was emitted
    assert all(e["type"] == "error" for e in events)
