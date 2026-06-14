"""Lightweight RPG rule engine: difficulty tables, combat math, initiative.

Kept deliberately small and pure so it is trivially unit-testable (Phase 6
rules_correctness evals assert this math exactly).
"""
from __future__ import annotations

from shared.state_schema import CharacterState, RollResult

# Difficulty classes by narrative difficulty band.
DC = {"trivial": 6, "easy": 9, "medium": 12, "hard": 15, "very_hard": 18, "legendary": 21}

# Damage by outcome for a successful attack (kept simple; expand via bestiary later).
ATTACK_DAMAGE = {"success": 6, "partial": 3, "failure": 0}


def difficulty_for(band: str) -> int:
    return DC.get(band, DC["medium"])


def apply_attack(target: CharacterState, result: RollResult) -> int:
    """Apply attack outcome to a target's HP. Returns damage dealt."""
    dmg = ATTACK_DAMAGE.get(result.result, 0)
    if dmg:
        target.health = max(0, target.health - dmg)
    return dmg


def initiative_order(actors: list[str], roller) -> list[tuple[str, int]]:
    """Roll initiative (d20) for each actor; return descending order."""
    rolls = [(a, roller.d20()) for a in actors]
    return sorted(rolls, key=lambda x: x[1], reverse=True)


def is_down(c: CharacterState) -> bool:
    return c.health <= 0
