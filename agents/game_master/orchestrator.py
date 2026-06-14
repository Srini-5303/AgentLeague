"""The Game Master orchestrator: run_turn() drives one full turn as an async
generator of SSE event dicts.

Pipeline (CLAUDE.md game loop):
  auth → resolve/own session → HITL gate → select agents →
  PARALLEL(lore search + character agents, each timeout-guarded) →
  resolve rolls → STREAM narration → (non-blocking) write state →
  choices + trace summary → done.

Design guarantees baked in:
  * Ownership: session.user_id must equal the JWT user_id (403 otherwise).
  * Partial results: a slow/failed agent degrades to a neutral response; the turn
    still completes (per-agent asyncio.wait_for timeout).
  * One in-flight turn per session (asyncio.Lock) to avoid lost-update races.
  * State write fires after the first streamed token, with one retry then a
    state_warning flag — never blocks the stream.
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from typing import AsyncIterator, Optional

from agents.game_master import choices as choices_mod
from agents.game_master import confirm as confirm_mod
from agents.game_master.character_agent import invoke_character_agent
from agents.game_master.context import build_agent_context, select_agents
from agents.game_master.state_update import apply_state_update, extract_state_update
from agents.game_master.summarize import maybe_summarize
from agents.game_master.synthesis import stream_synthesis
from shared.config import Settings, get_settings
from shared.dice import DiceRoller
from shared.interfaces import AuthProvider, KnowledgeStore, LLMClient, StateStore
from shared.interfaces.auth import AuthError
from shared.rules import apply_attack
from shared.state_schema import (
    AgentResponse,
    CampaignState,
    CharacterState,
    RollResult,
    TurnRequest,
    UserRecord,
    utcnow,
)
from shared.factory import build_tracer


class OwnershipError(Exception):
    """session.user_id != jwt user_id → HTTP 403."""


# Starting party for a brand-new campaign (companions; player added separately).
_STARTING_COMPANIONS = [
    CharacterState(agent="warrior", name="Bran Ironvale", char_class="Warrior", health=28, max_health=28, attack_bonus=4, armor_class=15),
    CharacterState(agent="mage", name="Lyra Vey", char_class="Mage", health=18, max_health=18, attack_bonus=2, armor_class=12),
    CharacterState(agent="rogue", name="Sable Dusk", char_class="Rogue", health=20, max_health=20, attack_bonus=3, armor_class=13),
    CharacterState(agent="healer", name="Mirra of the Root", char_class="Healer", health=20, max_health=20, attack_bonus=2, armor_class=12),
]


class GameMaster:
    def __init__(
        self,
        llm: LLMClient,
        knowledge: KnowledgeStore,
        state: StateStore,
        auth: AuthProvider,
        settings: Optional[Settings] = None,
    ):
        self.llm = llm
        self.knowledge = knowledge
        self.state = state
        self.auth = auth
        self.s = settings or get_settings()
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    # ── session bootstrap ────────────────────────────────────────────────
    async def _new_campaign(self, user_id: str) -> CampaignState:
        """Create and persist a brand-new campaign (fresh session) for a user."""
        session_id = str(uuid.uuid4())
        await self.state.create_user(UserRecord(id=user_id, session_id=session_id))
        party = [
            CharacterState(agent="player", name="Aria", char_class="Wanderer",
                           health=24, max_health=24, attack_bonus=3, armor_class=13, is_player=True),
            *[c.model_copy(deep=True) for c in _STARTING_COMPANIONS],
        ]
        fresh = CampaignState(session_id=session_id, user_id=user_id, party=party,
                              quest_log=["Find the Starwell Relic before Kael Thorn does."])
        await self.state.write_session(fresh)
        return fresh

    async def _resolve_session(self, user_id: str) -> CampaignState:
        user = await self.state.get_user(user_id)
        if user is None:
            return await self._new_campaign(user_id)
        existing = await self.state.get_session(user.session_id)
        if existing is None:
            # User record without a session (shouldn't happen) — rebuild empty.
            existing = CampaignState(session_id=user.session_id, user_id=user_id)
            await self.state.write_session(existing)
        return existing

    async def reset_session(self, authorization: Optional[str]) -> CampaignState:
        """Delete the player's saved campaign and start a fresh one. Validates the
        JWT first, then deletes the old session + user record (point deletes) and
        bootstraps a new campaign owned by the same user."""
        user_id = await self.auth.validate(authorization)
        async with self._locks[user_id]:
            user = await self.state.get_user(user_id)
            if user is not None:
                await self.state.delete_session(user.session_id)
                await self.state.delete_user(user_id)
            return await self._new_campaign(user_id)

    # ── the turn ─────────────────────────────────────────────────────────
    async def run_turn(self, bearer_token: str | None, req: TurnRequest) -> AsyncIterator[dict]:
        # 1. Auth (before any state/agent work).
        try:
            user_id = await self.auth.validate(bearer_token)
        except AuthError as e:
            yield {"type": "error", "status": 401, "message": str(e)}
            return

        state = await self._resolve_session(user_id)
        # 3. Ownership check.
        if state.user_id != user_id:
            yield {"type": "error", "status": 403, "message": "session ownership mismatch"}
            return

        lock = self._locks[state.session_id]
        if lock.locked():
            yield {"type": "error", "status": 409, "message": "a turn is already in progress"}
            return

        async with lock:
            async for event in self._process(state, user_id, req):
                yield event

    async def _process(self, state: CampaignState, user_id: str, req: TurnRequest) -> AsyncIterator[dict]:
        tracer = build_tracer(self.s)
        trace_id = uuid.uuid4().hex
        player_input = req.input.strip()

        # 5. HITL gate.
        if confirm_mod.needs_confirmation(player_input) and not confirm_mod.is_confirmed(player_input, req.confirm_token):
            yield confirm_mod.confirmation_payload(player_input)
            return

        # 6. Agent selection.
        agents_needed = select_agents(player_input, state)
        yield {"type": "agent_start", "agents": agents_needed}

        # 7. Parallel fan-out: lore search + character agents (each timeout-guarded).
        async def _lore():
            with tracer.span("gm.iq_query"):
                # Character-facing search excludes GM-only secrets.
                return await self.knowledge.search(
                    f"{state.location} {state.active_quest} {player_input}", top_k=3, include_secrets=False
                )

        async def _agent(name: str) -> AgentResponse:
            ctx = build_agent_context(name, player_input, state, [])
            with tracer.span(f"{name}.invoke"):
                try:
                    return await asyncio.wait_for(
                        invoke_character_agent(name, ctx, self.llm, self.s.character_model),
                        timeout=self.s.agent_timeout_seconds,
                    )
                except (asyncio.TimeoutError, Exception):
                    return AgentResponse(agent=name, action="is slow to react", emotional_state="strained", degraded=True)

        lore_task = asyncio.create_task(_lore())
        agent_tasks = [asyncio.create_task(_agent(n)) for n in agents_needed]
        lore = await lore_task
        responses = await asyncio.gather(*agent_tasks)

        # 9. Resolve rolls via the deterministic dice engine.
        roller = DiceRoller(self.s.dice_seed)
        rolls: list[RollResult] = []
        with tracer.span("gm.roll_resolution"):
            for r in responses:
                if r.roll_request:
                    result = roller.roll(r.roll_request)
                    if r.roll_request.kind == "attack":
                        self._apply_combat(state, r, result)
                    rolls.append(result)
                    yield {"type": "dice", **result.model_dump()}

        # GM-side lore (may include secrets to inform narration, never to reveal).
        gm_lore = await self.knowledge.search(
            f"{state.location} {state.active_quest}", top_k=3, include_secrets=True
        )

        # 10. Stream synthesis.
        narration_parts: list[str] = []
        durability_write: Optional[asyncio.Task] = None
        with tracer.span("gm.synthesis_stream"):
            async for token in stream_synthesis(
                player_input, state, gm_lore, list(responses), rolls, self.llm, self.s.narrator_model
            ):
                narration_parts.append(token)
                if durability_write is None:
                    # 11. Fire a non-blocking durability write right after the first token
                    # (turn++ & history) so progress survives a mid-stream disconnect.
                    durability_write = asyncio.create_task(self._commit_state(state, "".join(narration_parts)))
                yield {"type": "token", "text": token}

        narration = "".join(narration_parts).strip()
        if durability_write is None:  # degenerate: no tokens streamed
            durability_write = asyncio.create_task(self._commit_state(state, narration))
        await durability_write

        # 12. Post-stream, in parallel: structured state update + choices.
        with tracer.span("gm.state_update"):
            update_task = asyncio.create_task(
                extract_state_update(narration, state, self.llm, self.s.narrator_model)
            )
            choices_task = asyncio.create_task(
                choices_mod.generate_choices(narration, self.llm, self.s.narrator_model)
            )
            update, choices = await update_task, await choices_task

        apply_state_update(state, update)
        # Record the FULL turn narration for the "previously on" recap (the
        # durability write above only had the first streamed token).
        self._advance_history(state, narration)
        state.recent_history = await maybe_summarize(
            state.recent_history, state.turn, self.s.history_summarize_every,
            self.llm, self.s.narrator_model,
        )

        # 13. Authoritative final write (includes flags/location/quest/trace).
        agent_messages = {r.agent: r.speech for r in responses if r.speech}
        summary = tracer.build_summary(state.turn, trace_id, agent_messages)
        state.last_trace = summary
        state.updated_at = utcnow()
        state_warning = not await self._persist(state)

        yield {
            "type": "done",
            "turn": state.turn,
            "choices": choices,
            "rolls": [r.model_dump() for r in rolls],
            "trace_summary": summary.model_dump(),
            "party": [c.model_dump() for c in state.party],
            "quest_log": state.quest_log,
            "location": state.location,
            "active_quest": state.active_quest,
            "quest_stage": state.quest_stage,
            "world_flags": state.world_flags,
            **({"state_warning": True} if state_warning else {}),
        }

    # ── helpers ──────────────────────────────────────────────────────────
    def _apply_combat(self, state: CampaignState, resp: AgentResponse, result: RollResult) -> None:
        """Apply an attack result. Phase 1: attacks land on a generic foe tracked in
        world_flags['enemy_hp']; Phase 2 expands to full bestiary combatants."""
        from shared.rules import ATTACK_DAMAGE
        dmg = ATTACK_DAMAGE.get(result.result, 0)
        if dmg and "enemy_hp" in state.world_flags:
            state.world_flags["enemy_hp"] = max(0, int(state.world_flags["enemy_hp"]) - dmg)
            result.consequence = f"deals {dmg} damage"

    def _advance_history(self, state: CampaignState, narration: str) -> None:
        snippet = (narration[:240] + "…") if len(narration) > 240 else narration
        if snippet:
            state.recent_history.append(f"Turn {state.turn}: {snippet}")
        # Keep a little slack above 5; summarize.maybe_summarize() collapses the tail.
        if len(state.recent_history) > 8:
            state.recent_history = state.recent_history[-8:]

    async def _commit_state(self, state: CampaignState, narration: str) -> None:
        """Durability write fired during streaming: advance the turn so a mid-stream
        disconnect still persists progress. The recap history snippet is recorded
        post-stream from the full narration (see run_turn), not here."""
        state.turn += 1
        state.updated_at = utcnow()
        await self._persist(state)

    async def _persist(self, state: CampaignState) -> bool:
        """Write campaign state with one retry. Returns True if persisted."""
        for _ in range(2):
            try:
                await self.state.write_session(state)
                return True
            except Exception:
                continue
        return False
