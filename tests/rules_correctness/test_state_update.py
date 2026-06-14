from agents.game_master.state_update import apply_state_update
from shared.state_schema import CampaignState, CharacterState


def _state():
    return CampaignState(
        session_id="s", user_id="u",
        party=[CharacterState(agent="warrior", name="Bran", health=28, max_health=28)],
    )


def test_flag_advances_quest_stage():
    st = _state()
    assert st.quest_stage == 1
    apply_state_update(st, {"world_flags_set": {"sigil_read": True}, "location": None,
                            "quest_log_add": None, "party_damage": []})
    assert st.quest_stage == 2
    apply_state_update(st, {"world_flags_set": {"gate_open": True}, "location": None,
                            "quest_log_add": None, "party_damage": []})
    assert st.quest_stage == 3


def test_stage_never_regresses():
    st = _state()
    st.quest_stage = 3
    apply_state_update(st, {"world_flags_set": {"sigil_read": True}, "location": None,
                            "quest_log_add": None, "party_damage": []})
    assert st.quest_stage == 3


def test_location_and_questlog_and_hp():
    st = _state()
    apply_state_update(st, {
        "location": "Hedeby Reach",
        "quest_log_add": "Met the Iron Compact.",
        "world_flags_set": {},
        "party_damage": [{"agent": "warrior", "hp_delta": -10, "add_condition": "bleeding", "remove_condition": None}],
    })
    assert st.location == "Hedeby Reach"
    assert "Met the Iron Compact." in st.quest_log
    bran = st.party[0]
    assert bran.health == 18 and "bleeding" in bran.conditions


def test_hp_clamped_to_bounds():
    st = _state()
    apply_state_update(st, {"location": None, "quest_log_add": None, "world_flags_set": {},
                            "party_damage": [{"agent": "warrior", "hp_delta": -999, "add_condition": None, "remove_condition": None}]})
    assert st.party[0].health == 0
    apply_state_update(st, {"location": None, "quest_log_add": None, "world_flags_set": {},
                            "party_damage": [{"agent": "warrior", "hp_delta": 999, "add_condition": None, "remove_condition": None}]})
    assert st.party[0].health == 28


def test_none_update_is_safe():
    st = _state()
    apply_state_update(st, None)  # must not raise
    assert st.quest_stage == 1
