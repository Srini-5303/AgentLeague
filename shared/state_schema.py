"""Pydantic domain models for Eldervale campaign state and the turn protocol.

Extends the CLAUDE.md schema with the structured agent-response contract, dice
results, and the trace summary used by the telemetry panel. These models are the
single source of truth for what flows between the orchestrator, the agents, the
state store, and the frontend.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Party / character state ──────────────────────────────────────────────
class CharacterState(BaseModel):
    agent: str                       # "warrior" | "mage" | ... | "player"
    name: str
    char_class: str = "Adventurer"
    health: int = 20
    max_health: int = 20
    attack_bonus: int = 2
    armor_class: int = 12
    inventory: list[str] = Field(default_factory=list)   # soft cap 10
    conditions: list[str] = Field(default_factory=list)  # poisoned, blessed, ...
    trust_level: Optional[str] = None  # rival only: hostile→uncertain→neutral→ally
    is_player: bool = False


# ── The structured response every character agent must return ────────────
class RollRequest(BaseModel):
    actor: str
    check: str                        # "Stealth", "Arcana", "Attack", ...
    modifier: int = 0
    difficulty: int = 12              # DC (or target AC for attacks)
    kind: Literal["check", "attack", "initiative"] = "check"


class AgentResponse(BaseModel):
    agent: str
    speech: str = ""
    action: str = ""
    roll_request: Optional[RollRequest] = None
    emotional_state: str = "neutral"
    degraded: bool = False            # true if this is a timeout/parse fallback


class RollResult(BaseModel):
    actor: str
    check: str
    roll: int                         # natural d20
    total: int                        # roll + modifier
    difficulty: int
    result: Literal["success", "partial", "failure"]
    consequence: str = ""


# ── Telemetry ────────────────────────────────────────────────────────────
class SpanSummary(BaseModel):
    name: str
    ms: int


class TraceSummary(BaseModel):
    turn: int
    trace_id: str
    total_ms: int
    spans: list[SpanSummary] = Field(default_factory=list)
    agent_messages: dict[str, str] = Field(default_factory=dict)


# ── Campaign state (persisted per session) ───────────────────────────────
class CampaignState(BaseModel):
    session_id: str
    user_id: str
    campaign: str = "The Shards of Mani"
    location: str = "The Ruined Chapel"
    active_quest: str = "Find the Starwell Relic"
    quest_stage: int = 1
    turn: int = 0
    party: list[CharacterState] = Field(default_factory=list)
    world_flags: dict[str, Any] = Field(default_factory=dict)
    quest_log: list[str] = Field(default_factory=list)
    recent_history: list[str] = Field(default_factory=list)  # rolling last-5 summaries
    last_trace: Optional[TraceSummary] = None
    pending_confirmation: Optional[dict[str, Any]] = None     # HITL gate state
    updated_at: datetime = Field(default_factory=utcnow)
    etag: Optional[str] = None        # cosmos optimistic concurrency (ignored locally)

    def player(self) -> Optional[CharacterState]:
        return next((c for c in self.party if c.is_player), None)


class UserRecord(BaseModel):
    id: str                           # entra object id / dev user id
    session_id: str
    character_name: str = "Aria"
    created_at: datetime = Field(default_factory=utcnow)
    last_played: datetime = Field(default_factory=utcnow)


# ── Turn request from the frontend ───────────────────────────────────────
class TurnRequest(BaseModel):
    input: str
    confirm_token: Optional[str] = None   # echoes a prior HITL action_token to proceed
