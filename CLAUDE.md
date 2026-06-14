# CLAUDE.md — Fantasy RPG Multi-Agent System

## Project Overview

This is a multi-agent fantasy role-playing game built on **Microsoft Azure AI Foundry**. A human player goes on a text-based adventure orchestrated by a Game Master agent, which coordinates a cast of AI character agents. All agents are deployed as Hosted Agents in Foundry Agent Service.

---

## Platform Stack

| Layer | Technology |
|---|---|
| Agent hosting | Azure AI Foundry — Hosted Agents (Agent Service) |
| Model | Azure OpenAI (GPT-4o via Foundry) |
| Knowledge / Lore | Foundry IQ (vector search over campaign documents) |
| State persistence | Azure Cosmos DB (NoSQL, partitioned by session_id) |
| Dice / combat math | Code Interpreter tool (Foundry built-in) |
| Web inspiration | Bing Grounding / Web Search tool (Foundry built-in) |
| Streaming | Server-Sent Events (SSE) — GM narration streamed token by token |
| Auth | Microsoft Entra External ID (Azure AD B2C) — JWT per user |
| Observability | Azure Monitor + Application Insights + OpenTelemetry |
| Tracing | Distributed trace per turn; full agent call tree in App Insights |
| Container registry | Azure Container Registry (ACR) |
| Identity | Microsoft Entra ID managed identity per agent (no hardcoded secrets) |
| Frontend | React + TypeScript (Azure Static Web Apps) |

---

## Repository Structure

```
fantasy-rpg-agents/
├── CLAUDE.md                        # This file
├── PRD.md                           # Product requirements
├── README.md
│
├── agents/
│   ├── game_master/
│   │   ├── Dockerfile
│   │   ├── agent.py                 # GM orchestration logic
│   │   ├── system_prompt.md         # GM system prompt
│   │   ├── tools.py                 # Tool bindings (IQ, code, search)
│   │   ├── streaming.py             # SSE streaming helpers
│   │   ├── tracing.py               # OpenTelemetry span helpers
│   │   └── requirements.txt
│   ├── warrior/
│   │   ├── Dockerfile
│   │   ├── agent.py
│   │   └── system_prompt.md
│   ├── mage/
│   │   ├── Dockerfile
│   │   ├── agent.py
│   │   └── system_prompt.md
│   ├── rogue/
│   │   ├── Dockerfile
│   │   ├── agent.py
│   │   └── system_prompt.md
│   ├── healer/
│   │   ├── Dockerfile
│   │   ├── agent.py
│   │   └── system_prompt.md
│   └── rival/
│       ├── Dockerfile
│       ├── agent.py
│       └── system_prompt.md
│
├── shared/
│   ├── state_schema.py              # Pydantic models for campaign state
│   ├── dice.py                      # Dice roll logic
│   ├── rules.py                     # Lightweight RPG rule engine
│   ├── foundry_client.py            # Foundry Agent Service SDK wrapper
│   ├── auth.py                      # JWT validation + user→session lookup
│   └── tracing.py                   # Shared OpenTelemetry helpers
│
├── knowledge/
│   ├── world_overview.md
│   ├── locations.md
│   ├── factions.md
│   ├── characters.md
│   ├── quests.md
│   ├── items_and_artifacts.md
│   ├── bestiary.md
│   ├── homebrew_rules.md
│   └── session_notes_template.md
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── auth/
│   │   │   ├── MsalProvider.tsx     # Entra External ID MSAL setup
│   │   │   └── useAuth.ts           # Auth hook (login, logout, getToken)
│   │   ├── components/
│   │   │   ├── AdventureLog.tsx     # Streaming text display
│   │   │   ├── CharacterSheet.tsx
│   │   │   ├── DiceRoll.tsx
│   │   │   ├── QuestJournal.tsx
│   │   │   └── AgentTelemetry.tsx   # Gantt-style trace timeline
│   │   └── api/
│   │       ├── foundryClient.ts     # SSE stream consumer
│   │       └── sessionClient.ts     # Session resume / state fetch
│   └── package.json
│
├── infra/
│   ├── main.bicep                   # Azure infrastructure as code
│   ├── agents.bicep                 # Hosted agent definitions
│   ├── cosmos.bicep                 # State + users DB (two containers)
│   ├── acr.bicep                    # Container registry
│   └── auth.bicep                   # Entra External ID tenant config
│
└── tests/
    ├── story_consistency/           # Eval set for narrative coherence
    ├── rules_correctness/           # Eval set for rule enforcement
    └── agent_behavior/              # Per-agent personality tests
```

---

## Agent Architecture

### Game Master Agent (Orchestrator)

The GM is the **sole orchestrator**. It never appears as a character. It:

1. Validates the player's JWT and resolves `user_id` → `session_id`
2. Reads current `CampaignState` from Cosmos DB (point read by `session_id`)
3. Queries Foundry IQ for scene-relevant lore
4. Decides which character agents to invoke (1–4 per turn)
5. Invokes all required character agents **in parallel** via `asyncio.gather()`
6. Uses Code Interpreter to resolve any dice rolls
7. **Streams** the synthesized narration back to the frontend via SSE
8. Writes updated `CampaignState` to Cosmos DB
9. Emits OpenTelemetry spans for every step

**Tools available to GM:**
- `foundry_iq_search` — retrieve world lore
- `code_interpreter` — dice rolls, combat resolution
- `web_search` — public-domain inspiration only
- `cosmos_read` / `cosmos_write` — campaign state (point ops only)
- `invoke_agent(agent_id, context)` — call character agents

### Character Agents (Warrior, Mage, Rogue, Healer, Rival)

Each character agent:
- Has a fixed system prompt defining personality, backstory, abilities
- Receives a structured context object from the GM
- Returns a structured response: `{ speech, action, roll_request, emotional_state }`
- Does NOT call other agents directly
- Has limited tool access based on their in-story role

**Character agent tool access:**

| Agent | Tools |
|---|---|
| Warrior | code_interpreter (combat rolls only) |
| Mage | foundry_iq_search, code_interpreter (arcana rolls) |
| Rogue | code_interpreter (stealth/trap rolls), cosmos_read (contacts/secrets) |
| Healer | foundry_iq_search (religion/healing lore), code_interpreter (medicine rolls) |
| Rival | foundry_iq_search, cosmos_read (world flags) |

---

## Authentication and Session Isolation

### Auth Flow

```
1. Player opens app → redirected to Entra External ID login
2. Player authenticates (email/password or social provider)
3. Entra issues a JWT containing user_id (Entra object ID)
4. Frontend stores JWT in memory (NOT localStorage)
5. Every API request sends JWT in Authorization: Bearer header
6. GM agent validates JWT signature via Entra JWKS endpoint
7. GM extracts user_id from JWT claims
8. GM looks up session_id from users container (point read by user_id)
9. All Cosmos DB reads/writes use that session_id as partition key
```

### JWT Validation (shared/auth.py)

```python
from azure.identity import ManagedIdentityCredential
from msal import PublicClientApplication
import jwt

ENTRA_TENANT = "your-tenant-id"
ENTRA_CLIENT_ID = "your-client-id"
JWKS_URI = f"https://login.microsoftonline.com/{ENTRA_TENANT}/discovery/v2.0/keys"

async def validate_jwt(token: str) -> str:
    """Validates JWT and returns user_id. Raises 401 on failure."""
    jwks_client = jwt.PyJWKClient(JWKS_URI)
    signing_key = jwks_client.get_signing_key_from_jwt(token)
    payload = jwt.decode(token, signing_key.key, algorithms=["RS256"],
                         audience=ENTRA_CLIENT_ID)
    return payload["oid"]  # Entra object ID = user_id

async def resolve_session(user_id: str, cosmos_client) -> str:
    """Returns session_id for a user. Creates new session if first login."""
    users_container = cosmos_client.get_container_client("users")
    try:
        item = users_container.read_item(item=user_id, partition_key=user_id)
        return item["session_id"]
    except CosmosResourceNotFoundError:
        session_id = str(uuid.uuid4())
        users_container.create_item({
            "id": user_id,
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat()
        })
        return session_id
```

### Cosmos DB Containers

**Container: `users`** — partition key: `user_id`
```json
{
  "id": "<entra-object-id>",
  "session_id": "<uuid>",
  "character_name": "Aria",
  "created_at": "...",
  "last_played": "..."
}
```

**Container: `sessions`** — partition key: `session_id`
```json
{
  "id": "<session_id>",
  "user_id": "<entra-object-id>",
  "campaign_state": { ... },
  "turn": 14,
  "updated_at": "..."
}
```

The GM always verifies `session.user_id == jwt.user_id` before processing any turn.
If they don't match → 403, no processing occurs.

### Cosmos DB Latency Profile

All operations are point reads/writes keyed by partition key:

| Operation | Typical Latency |
|---|---|
| Point read (session state) | < 10ms P99 |
| Single document write | < 15ms P99 |
| Total per turn (read + write) | ~25–50ms |

Never query across partitions. Never use `SELECT *` queries on these containers.

---

## Latency Architecture

### Parallelized Agent Invocation

Character agents do not depend on each other's output. The GM fires all required agents
simultaneously and awaits all results before synthesizing.

```python
# agents/game_master/agent.py

async def run_turn(player_input: str, state: CampaignState,
                   agents_needed: list[str], trace_id: str) -> AsyncGenerator:

    # Step 1: parallel — IQ query + agent calls fire at the same time
    lore_task = asyncio.create_task(query_foundry_iq(state))
    agent_tasks = {
        name: asyncio.create_task(
            invoke_character_agent(name, build_context(state, player_input), trace_id)
        )
        for name in agents_needed
    }

    # Step 2: await IQ (usually returns first, ~300ms)
    lore = await lore_task

    # Step 3: await all agents (parallel — slowest wins, ~3-4s)
    agent_responses = {
        name: await task for name, task in agent_tasks.items()
    }

    # Step 4: resolve rolls (Code Interpreter, ~200ms)
    roll_results = await resolve_rolls(agent_responses)

    # Step 5: STREAM synthesis — yields tokens as they arrive
    async for token in stream_gm_synthesis(lore, agent_responses, roll_results, state):
        yield token  # SSE chunk to frontend

    # Step 6: write state (non-blocking, fires after first token yielded)
    asyncio.create_task(write_state(state, roll_results))
```

### Latency Budget (P90, parallelized)

| Step | Time | Parallelized? |
|---|---|---|
| JWT validation | ~5ms | — |
| Cosmos read (state) | ~10ms | — |
| Foundry IQ query | ~300ms | Yes — runs alongside agent calls |
| Character agent calls (3 agents) | ~3–4s | Yes — all fire simultaneously |
| Code Interpreter (rolls) | ~200ms | After agents return |
| GM synthesis stream (first token) | ~1s | Sequential — needs agent results |
| Cosmos write (state) | ~15ms | Non-blocking — fires after stream starts |
| **Time to first streamed token** | **~4–5s** | |
| **Full narration visible** | **~7–8s** | |

### Streaming (SSE)

The GM streams its synthesis narration token by token. The player sees text appearing
immediately once synthesis begins — the ~4s agent processing phase happens invisibly.

**Frontend UX during a turn:**
```
0s    — Player submits action
0–4s  — "The party deliberates..." loading indicator
4s    — First token of narration appears, streams word by word
7–8s  — Narration complete, choices appear, dice results shown
```

**Backend SSE endpoint:**
```python
# agents/game_master/streaming.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.post("/turn")
async def turn(request: TurnRequest, authorization: str = Header()):
    user_id = await validate_jwt(authorization.replace("Bearer ", ""))
    session_id = await resolve_session(user_id, cosmos_client)

    async def event_stream():
        # Emit agent status events before narration starts
        yield f"data: {json.dumps({'type': 'agent_start', 'agents': agents_needed})}\n\n"

        async for token in run_turn(request.input, state, agents_needed, trace_id):
            yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'choices': choices, 'rolls': rolls})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

**Frontend SSE consumer:**
```typescript
// frontend/src/api/foundryClient.ts
export async function streamTurn(input: string, token: string,
                                  onToken: (t: string) => void,
                                  onDone: (data: TurnResult) => void) {
  const response = await fetch("/turn", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
    body: JSON.stringify({ input }),
  });

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    const lines = decoder.decode(value).split("\n\n");
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));
      if (event.type === "token") onToken(event.text);
      if (event.type === "done") onDone(event);
    }
  }
}
```

---

## Distributed Tracing

Every turn produces a single distributed trace visible in Azure Application Insights.
The trace tree shows every agent call, tool call, and their latencies.

### Trace Structure Per Turn

```
Turn trace (trace_id: abc123)
├── gm.state_read          (10ms)
├── gm.iq_query            (310ms)
├── agents.parallel_invoke
│   ├── warrior.invoke     (2900ms)
│   │   └── warrior.tool.code_interpreter  (120ms)
│   ├── mage.invoke        (3200ms)
│   │   └── mage.tool.foundry_iq_search    (280ms)
│   └── rogue.invoke       (2700ms)
├── gm.roll_resolution     (190ms)
├── gm.synthesis_stream    (3100ms — time to full narration)
└── gm.state_write         (15ms)
```

### OpenTelemetry Instrumentation

```python
# shared/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

tracer = trace.get_tracer("fantasy-rpg")

def new_turn_span(trace_id: str):
    return tracer.start_as_current_span(
        "gm.turn",
        attributes={"trace_id": trace_id, "service": "game-master"}
    )

def agent_span(agent_name: str, parent_ctx):
    return tracer.start_as_current_span(
        f"{agent_name}.invoke",
        context=parent_ctx,
        attributes={"agent": agent_name}
    )
```

Trace context is passed to each character agent invocation so their spans
are children of the parent GM turn span — the full tree is stitched in App Insights.

### Telemetry Panel (Frontend)

The `AgentTelemetry.tsx` component fetches the trace summary for the last turn
and renders a Gantt-style horizontal timeline:

```
Turn 14  |  Total: 6.8s
─────────────────────────────────────────────────
IQ Query    ████ 310ms
Warrior     ████████████████████████ 2900ms
Mage        ████████████████████████████ 3200ms
Rogue       ██████████████████████ 2700ms
Rolls       ██ 190ms
Synthesis   ████████████████████████████ 3100ms (streaming)
State Write █ 15ms
─────────────────────────────────────────────────
Agent messages: [Warrior: "I'll take point..."] [Mage: "The sigil matches..."]
```

Toggled via a "Show Agent Reasoning" button — off by default for players,
on by default in demo/dev mode.

---

## Shared State Schema

```python
# shared/state_schema.py

from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class CharacterState(BaseModel):
    agent: str
    name: str
    health: int
    max_health: int
    inventory: List[str]          # max 10 items
    conditions: List[str]         # poisoned, stunned, blessed, etc.
    trust_level: Optional[str]    # rival only: hostile→uncertain→neutral→ally

class TurnTrace(BaseModel):
    turn_id: str
    trace_id: str
    agents_called: List[str]
    tool_calls: List[dict]
    latency_ms: int
    agent_messages: Dict[str, str]  # agent_name → raw response

class CampaignState(BaseModel):
    session_id: str
    user_id: str
    campaign: str
    location: str
    active_quest: str
    turn: int
    party: List[CharacterState]
    world_flags: Dict[str, any]
    quest_log: List[str]
    recent_history: List[str]     # last 5 turn summaries (rolling)
    last_trace: Optional[TurnTrace]
    updated_at: datetime
```

---

## Dice Roll Protocol

All rolls go through Code Interpreter. The GM requests a roll with a structured payload:

```python
roll_request = {
    "actor": "Rogue Agent",
    "check": "Stealth",
    "modifier": 3,
    "difficulty": 14
}

# Code Interpreter executes:
import random
roll = random.randint(1, 20) + modifier
result = "success" if roll >= difficulty else ("partial" if roll >= difficulty - 4 else "failure")
```

Result returned to GM:
```json
{
  "actor": "Rogue Agent",
  "check": "Stealth",
  "roll": 17,
  "difficulty": 14,
  "result": "success",
  "consequence": "The Rogue slips past the torchlight."
}
```

---

## Foundry IQ Integration

### Upload Knowledge Base

Before deploying, upload all files in `knowledge/` to a Foundry IQ index named `eldervale-campaign`.

```bash
az ai foundry iq upload \
  --index eldervale-campaign \
  --source ./knowledge/ \
  --chunk-size 512 \
  --overlap 64
```

### GM Query Pattern

```python
# Runs in parallel with agent invocations — does not block them
lore_results = await foundry_iq.search(
    index="eldervale-campaign",
    query=f"{current_location} {active_quest} {relevant_npc}",
    top_k=3
)
```

### Knowledge Document Format

```markdown
# [Entity Name]

**Type:** [Location | Faction | Character | Quest | Item | Monster]
**Tags:** tag1, tag2, tag3

## Summary
One paragraph overview.

## Known Facts
- Fact players can discover

## Secrets
- [GM ONLY] Secret the players don't know yet

## Related Entities
- EntityName1
```

---

## Hosted Agent Deployment

### Container Pattern

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "agent.py"]
```

### Deployment via Bicep

```bicep
resource gameMasterAgent 'Microsoft.AI/agents@2024-01-01' = {
  name: 'game-master-agent'
  properties: {
    image: '${acr.loginServer}/game-master:latest'
    identity: { type: 'SystemAssigned' }
    tools: ['code_interpreter', 'foundry_iq', 'web_search']
    storageConnection: cosmosDb.connectionString
    telemetry: { appInsightsConnectionString: appInsights.connectionString }
  }
}
```

### Agent Invocation with Trace Context

```python
# shared/foundry_client.py
from azure.ai.foundry import AgentClient
from opentelemetry.propagate import inject

async def invoke_character_agent(agent_id: str, context: dict,
                                  parent_trace_id: str) -> dict:
    headers = {}
    inject(headers)  # propagates trace context to child agent span

    client = AgentClient(endpoint=FOUNDRY_ENDPOINT)
    response = await client.invoke(
        agent_id=agent_id,
        messages=[{"role": "user", "content": json.dumps(context)}],
        headers=headers
    )
    return json.loads(response.content)
```

---

## Game Loop (Turn by Turn)

```
1.  Player sends input + JWT → Frontend → GM SSE endpoint
2.  GM validates JWT → resolves user_id → session_id
3.  GM verifies session.user_id == jwt.user_id (403 if mismatch)
4.  GM reads CampaignState from Cosmos DB (point read, ~10ms)
5.  GM opens OpenTelemetry turn span
6.  GM fires IQ query + all agent invocations in parallel
7.  Frontend shows "party deliberates" indicator (~0–4s)
8.  IQ results arrive (~300ms); agents arrive (~3–4s)
9.  GM resolves roll_requests via Code Interpreter
10. GM begins streaming synthesis → first SSE token → frontend starts rendering
11. GM fires async state write to Cosmos DB (non-blocking)
12. Stream completes → GM emits choices + roll results + trace summary
13. Frontend renders choices; AgentTelemetry panel updates with trace
```

---

## Frontend Requirements

- **Adventure Log** — SSE text stream renders word by word; GM text highlighted
- **Loading Indicator** — "The party deliberates..." shown during 0–4s processing phase
- **Character Sheets** — health bars, inventory, conditions per party member
- **Dice Roll Visualizer** — animated roll display when checks occur
- **Quest Journal** — active/completed quests with clue tracking
- **Agent Telemetry Panel** — Gantt timeline of agent calls, latency, tool calls, agent messages (toggle)
- **Player Input** — text field + submit + 3–4 quick-action buttons from GM choices
- **Auth** — MSAL login/logout via Entra External ID; JWT held in memory only

---

## Environment Variables

```bash
FOUNDRY_ENDPOINT=https://<your-foundry-endpoint>.azure.com
FOUNDRY_IQ_INDEX=eldervale-campaign
COSMOS_DB_ENDPOINT=https://<account>.documents.azure.com
COSMOS_DB_DATABASE=fantasy-rpg
COSMOS_USERS_CONTAINER=users
COSMOS_SESSIONS_CONTAINER=sessions
ACR_LOGIN_SERVER=<registry>.azurecr.io
APPINSIGHTS_CONNECTION_STRING=InstrumentationKey=...
ENTRA_TENANT_ID=<tenant-id>
ENTRA_CLIENT_ID=<client-id>
GAME_MASTER_AGENT_ID=<agent-id>
WARRIOR_AGENT_ID=<agent-id>
MAGE_AGENT_ID=<agent-id>
ROGUE_AGENT_ID=<agent-id>
HEALER_AGENT_ID=<agent-id>
RIVAL_AGENT_ID=<agent-id>
```

Never hardcode credentials. All agents authenticate via Entra managed identity.

---

## Testing

### Story Consistency Evals
- Input: sequence of player actions
- Expected: narrative stays consistent, world flags update correctly
- Assert: location names match IQ lore, character names stable across turns

### Rules Correctness Evals
- Input: structured combat scenario
- Expected: correct dice math, correct HP deduction
- Assert: roll results match Code Interpreter output exactly

### Agent Personality Evals
- Input: emotional scene prompt per agent
- Expected: response matches defined personality traits
- Assert: Warrior doesn't cast spells, Mage doesn't intimidate

### Auth + Isolation Tests
- Assert: user A's JWT cannot access user B's session_id
- Assert: missing JWT returns 401 before any agent is called
- Assert: state write always includes correct user_id back-reference

---

## Key Constraints

- The GM is the ONLY agent that calls other agents
- Character agents NEVER communicate directly with each other
- Character agents NEVER break the fourth wall
- Dice rolls ALWAYS go through Code Interpreter, never ad-hoc text
- All character agent calls MUST be parallelized with asyncio.gather()
- GM synthesis MUST stream via SSE — never buffer and return all at once
- State ALWAYS writes to Cosmos DB before the SSE stream closes
- State writes use the session_id partition key — NEVER cross-partition queries
- JWT validation MUST happen before any Cosmos read or agent call
- session.user_id MUST be verified against jwt.user_id on every turn
- OpenTelemetry spans MUST be emitted for every agent call and tool call
- Trace context MUST be propagated to child agent invocations
- Foundry IQ is the source of truth for world lore — agents must not invent facts
- Secrets in knowledge files are NEVER returned to the player directly
- Human-in-the-loop confirmation required for irreversible actions
