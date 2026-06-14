"""Human-in-the-loop gate for irreversible actions (PRD 4.11).

Detects when a player's input describes a truly irreversible act — killing a
companion, betraying the party, destroying an artifact/Shard. The orchestrator
emits a `confirm` event with an action_token and stops; the player must resubmit
with that token to actually resolve it. The token is a salted hash of the input so
a stale or spoofed token can't auto-confirm a different action.
"""
from __future__ import annotations

import hashlib

_IRREVERSIBLE = [
    "kill", "murder", "execute", "betray", "abandon", "sacrifice",
    "destroy the", "shatter the", "burn the", "break the shard", "drink the",
]


def _token(player_input: str) -> str:
    return hashlib.sha256(f"eldervale::{player_input.strip().lower()}".encode()).hexdigest()[:16]


def needs_confirmation(player_input: str) -> bool:
    text = player_input.lower()
    return any(kw in text for kw in _IRREVERSIBLE)


def confirmation_payload(player_input: str) -> dict:
    return {
        "type": "confirm",
        "prompt": (
            "This choice cannot be undone. The saga will remember it. "
            "Are you certain you wish to proceed?"
        ),
        "action_token": _token(player_input),
        "action": player_input,
    }


def is_confirmed(player_input: str, confirm_token: str | None) -> bool:
    return bool(confirm_token) and confirm_token == _token(player_input)
