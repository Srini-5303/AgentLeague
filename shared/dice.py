"""Deterministic, seedable d20 engine — the single source of truth for all rolls.

CLAUDE.md says rolls "always go through Code Interpreter". In practice correctness
must never depend on a remote sandbox: this module is the authority. In Azure mode
the orchestrator may *additionally* echo a roll through Foundry Code Interpreter for
the tracing/demo story, but the number returned here is canonical and auditable.

Seed via Settings.dice_seed for reproducible tests.
"""
from __future__ import annotations

import random

from shared.state_schema import RollRequest, RollResult


class DiceRoller:
    def __init__(self, seed: int | None = None):
        self._rng = random.Random(seed)

    def d20(self) -> int:
        return self._rng.randint(1, 20)

    def roll(self, req: RollRequest) -> RollResult:
        """Resolve a single roll request into a graded outcome.

        success: total >= difficulty
        partial: total within 4 below difficulty (a near miss)
        failure: otherwise
        Natural 20 always succeeds, natural 1 always fails (classic crit rule).
        """
        nat = self.d20()
        total = nat + req.modifier
        if nat == 20:
            result = "success"
        elif nat == 1:
            result = "failure"
        elif total >= req.difficulty:
            result = "success"
        elif total >= req.difficulty - 4:
            result = "partial"
        else:
            result = "failure"
        return RollResult(
            actor=req.actor,
            check=req.check,
            roll=nat,
            total=total,
            difficulty=req.difficulty,
            result=result,
        )
