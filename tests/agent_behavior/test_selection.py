from agents.game_master.context import select_agents
from shared.state_schema import CampaignState


def _state(**flags):
    return CampaignState(session_id="s", user_id="u", world_flags=dict(flags))


def test_combat_words_pick_warrior():
    chosen = select_agents("I attack the enemy and defend the gate", _state())
    assert "warrior" in chosen


def test_arcana_words_pick_mage():
    chosen = select_agents("I study the glowing rune and ancient sigil", _state())
    assert "mage" in chosen


def test_stealth_words_pick_rogue():
    assert "rogue" in select_agents("I sneak and pick the lock quietly", _state())


def test_rival_gated_unless_present_or_named():
    # Rival should NOT appear from generic words alone.
    chosen = select_agents("I bargain for a better deal", _state())
    assert "rival" not in chosen
    # Appears when explicitly named...
    assert "rival" in select_agents("I challenge Kael to a duel", _state())
    # ...or already present in the scene.
    assert "rival" in select_agents("I bargain for a better deal", _state(rival_present=True))


def test_default_when_ambiguous():
    chosen = select_agents("I look around", _state())
    assert chosen == ["warrior", "mage"]


def test_capped_by_max_agents(monkeypatch):
    from shared import config
    s = config.get_settings()
    monkeypatch.setattr(s, "max_agents_per_turn", 2)
    chosen = select_agents("I attack, sneak, study the rune, and heal", _state())
    assert len(chosen) <= 2
