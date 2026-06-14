from shared.dice import DiceRoller
from shared.rules import apply_attack, difficulty_for, initiative_order
from shared.state_schema import CharacterState, RollRequest, RollResult


def test_seed_is_deterministic():
    a = [DiceRoller(42).d20() for _ in range(5)]
    b = [DiceRoller(42).d20() for _ in range(5)]
    assert a == b


def test_grading_bands():
    roller = DiceRoller(1)
    # Force totals by modifier so we exercise success/partial/failure deterministically.
    # With seed=1 the first d20 is fixed; assert the grade matches the rule, not a literal.
    req = RollRequest(actor="x", check="c", modifier=0, difficulty=12)
    r = DiceRoller(1).roll(req)
    if r.roll in (20,):
        assert r.result == "success"
    elif r.roll == 1:
        assert r.result == "failure"
    elif r.total >= 12:
        assert r.result == "success"
    elif r.total >= 8:
        assert r.result == "partial"
    else:
        assert r.result == "failure"


def test_nat20_always_succeeds_nat1_always_fails():
    # Brute force seeds until we observe a natural 20 and a natural 1.
    saw20 = saw1 = False
    for seed in range(500):
        r = DiceRoller(seed).roll(RollRequest(actor="x", check="c", modifier=-50, difficulty=99))
        if r.roll == 20:
            assert r.result == "success"
            saw20 = True
        r2 = DiceRoller(seed).roll(RollRequest(actor="x", check="c", modifier=50, difficulty=1))
        if r2.roll == 1:
            assert r2.result == "failure"
            saw1 = True
        if saw20 and saw1:
            break
    assert saw20 and saw1


def test_attack_damage_application():
    target = CharacterState(agent="enemy", name="Draugr", health=18, max_health=18)
    success = RollResult(actor="bran", check="Attack", roll=15, total=19, difficulty=13, result="success")
    dmg = apply_attack(target, success)
    assert dmg == 6 and target.health == 12
    miss = RollResult(actor="bran", check="Attack", roll=3, total=5, difficulty=13, result="failure")
    assert apply_attack(target, miss) == 0 and target.health == 12


def test_difficulty_table():
    assert difficulty_for("easy") == 9
    assert difficulty_for("legendary") == 21
    assert difficulty_for("unknown") == 12  # defaults to medium


def test_initiative_descending():
    order = initiative_order(["a", "b", "c"], DiceRoller(3))
    rolls = [r for _, r in order]
    assert rolls == sorted(rolls, reverse=True)
