"""Local function-agent: turns a character's system prompt + structured context
into a parsed, validated AgentResponse.

In Azure mode the same system_prompt.md text becomes a Foundry agent's instructions
and this call routes through the Foundry responses API instead — the orchestrator
contract (an AgentResponse) is identical, which is what keeps the swap config-only.

Robustness: strict JSON schema is requested where the provider supports it; the
result is tolerantly parsed; on any failure a neutral, in-character degraded
response is returned so a single bad agent never breaks the turn.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from shared.interfaces.llm import LLMClient, LLMMessage
from shared.state_schema import AgentResponse, RollRequest

_AGENT_DIR = Path(__file__).resolve().parent.parent  # agents/

# JSON schema the character agents must satisfy (kept strict-mode friendly).
RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "speech": {"type": "string"},
        "action": {"type": "string"},
        "emotional_state": {"type": "string"},
        "roll_request": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "properties": {
                "check": {"type": "string"},
                "modifier": {"type": "integer"},
                "difficulty": {"type": "integer"},
                "kind": {"type": "string", "enum": ["check", "attack", "initiative"]},
            },
            "required": ["check", "modifier", "difficulty", "kind"],
        },
    },
    "required": ["speech", "action", "emotional_state", "roll_request"],
}


@lru_cache(maxsize=8)
def load_system_prompt(agent: str) -> str:
    return (_AGENT_DIR / agent / "system_prompt.md").read_text(encoding="utf-8")


_OUTPUT_INSTRUCTION = (
    "Respond ONLY with a JSON object matching this shape: "
    '{"speech": str (what you say aloud, in character), '
    '"action": str (what you physically do this turn), '
    '"emotional_state": str (one word), '
    '"roll_request": null OR {"check": str, "modifier": int, "difficulty": int, '
    '"kind": "check"|"attack"|"initiative"}}. '
    "Request a roll only when the outcome is genuinely uncertain. No prose outside the JSON."
)


def _neutral(agent: str) -> AgentResponse:
    return AgentResponse(
        agent=agent,
        speech="",
        action="holds back, watchful",
        emotional_state="wary",
        degraded=True,
    )


def _parse(agent: str, raw: str) -> AgentResponse:
    data = json.loads(raw)
    rr = data.get("roll_request")
    roll = None
    if rr:
        roll = RollRequest(
            actor=agent,
            check=rr.get("check", "check"),
            modifier=int(rr.get("modifier", 0)),
            difficulty=int(rr.get("difficulty", 12)),
            kind=rr.get("kind", "check"),
        )
    return AgentResponse(
        agent=agent,
        speech=data.get("speech", ""),
        action=data.get("action", ""),
        emotional_state=data.get("emotional_state", "neutral"),
        roll_request=roll,
    )


async def invoke_character_agent(
    agent: str,
    context: dict,
    llm: LLMClient,
    model: str,
) -> AgentResponse:
    messages: list[LLMMessage] = [
        {"role": "system", "content": load_system_prompt(agent) + "\n\n" + _OUTPUT_INSTRUCTION},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
    ]
    try:
        raw = await llm.complete(messages, model=model, json_schema=RESPONSE_SCHEMA, temperature=0.85)
        return _parse(agent, raw)
    except Exception:
        # One repair attempt: ask plainly for valid JSON, no schema constraint.
        try:
            raw = await llm.complete(
                messages + [{"role": "user", "content": "Return ONLY the JSON object, nothing else."}],
                model=model,
                json_schema=RESPONSE_SCHEMA,
                temperature=0.3,
            )
            return _parse(agent, raw)
        except Exception:
            return _neutral(agent)
