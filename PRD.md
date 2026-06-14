# PRD — Fantasy RPG Multi-Agent System
## Product Requirements Document

**Version:** 1.1  
**Platform:** Microsoft Azure AI Foundry  
**Status:** In Development

---

## 1. Product Vision

Build a text-based fantasy role-playing game where every character in the party is a live AI agent with its own personality, memory, and reasoning — all orchestrated by a Game Master agent running on Azure AI Foundry. The player makes decisions turn by turn; the AI handles the world, the rules, the story, and the cast.

The system should feel like playing a tabletop RPG with a skilled dungeon master and a full party of AI companions, each with distinct voices, agendas, and reactions.

---

## 2. Problem Statement

Existing AI RPG tools either:
- Use a single model that tries to play all roles at once, producing flat, inconsistent character voices
- Require the player to manually manage rules, rolls, and party state
- Have no persistent world memory between sessions
- Cannot retrieve structured world lore at runtime to stay grounded

This system solves all four problems with a true multi-agent architecture, Foundry IQ lore grounding, Code Interpreter for deterministic rules, and persistent state via Cosmos DB.

---

## 3. Target Users

| User | Description |
|---|---|
| Tabletop RPG fans | Want a solo RPG experience without scheduling a group |
| Casual game players | Want narrative adventure without learning complex game systems |
| AI/developer audience | Want to see multi-agent orchestration in a compelling demo |
| Hackathon evaluators | Want a technically impressive, architecturally sound showcase |

---

## 4. Core Features

### 4.1 Authentication and Session Management
- Players sign in via Microsoft Entra External ID (email/password or social provider)
- Each player receives a JWT on login containing their Entra user ID
- JWT is stored in memory only — never in localStorage or cookies
- Every API request carries the JWT in the Authorization header
- The GM validates the JWT and resolves it to a `session_id` before any processing
- The GM verifies `session.user_id == jwt.user_id` on every turn — no cross-session access is possible
- Players automatically resume their saved campaign on login — no "load game" screen needed
- New players get a fresh `session_id` and are guided through character creation

### 4.2 Character Creation
- Player names their character and picks a class (Fighter, Wizard, Ranger, Cleric, or custom)
- System generates starting stats, inventory, and a brief backstory hook
- Player's character is tracked alongside AI party members in shared state

### 4.3 Game Master Orchestration
- GM agent receives every player input after JWT validation
- GM queries Foundry IQ for lore in parallel with agent invocations — not before
- GM invokes all required character agents simultaneously via asyncio.gather()
- GM uses Code Interpreter to resolve all dice rolls after agents respond
- GM streams the synthesized narration token by token via SSE
- GM writes updated campaign state to Cosmos DB non-blocking after stream starts
- GM presents 3–4 player choices at the end of each turn

### 4.4 AI Character Agents
Five persistent character agents, each deployed as a Hosted Agent:

| Agent | Name | Role | Personality |
|---|---|---|---|
| Warrior | Bran Ironvale | Frontline protector | Brave, direct, suspicious of magic |
| Mage | Lyra Vey | Arcane scholar | Curious, analytical, slightly arrogant |
| Rogue | Sable Dusk | Scout and trickster | Witty, skeptical, opportunistic |
| Healer | Mirra of the Root | Support and moral compass | Compassionate, principled, observant |
| Rival | Kael Thorn | Recurring story antagonist/ally | Charismatic, proud, unpredictable |

Each agent speaks in character, reacts to story events based on their backstory,
and returns a structured response the GM can parse and synthesize.

### 4.5 Streaming Narration
- GM narration streams to the frontend via Server-Sent Events (SSE)
- Player sees text appearing word by word — no waiting for a full response
- Loading indicator shown during the parallel agent processing phase (~0–4s)
- First streamed token appears ~4–5s after player submits input
- Full narration visible ~7–8s after submission

### 4.6 Dice Roll System
- All checks use d20 + modifier vs difficulty class
- Outcomes: success, partial success, failure
- Rolls executed deterministically by Code Interpreter — auditable and consistent
- Roll results surfaced to the player with full context

### 4.7 World Lore (Foundry IQ)
- Campaign world "Eldervale" stored as a structured knowledge base in Foundry IQ
- Covers: world overview, 5+ locations, 3 factions, character backstories, 3 quests, 5 artifacts, 5 monsters, homebrew rules
- GM retrieves relevant lore in parallel with agent calls each turn
- Secrets in lore are marked GM-only and never surfaced directly to the player

### 4.8 Persistent Campaign State
- Full campaign state persisted to Cosmos DB after every turn
- Cosmos DB partitioned by `session_id` — all ops are point reads/writes (~10–15ms)
- State includes: location, active quest, party health/inventory/conditions, world flags, quest log, session summary
- State survives session restarts and device changes — resume is automatic on login

### 4.9 Combat System
- Turn-based combat triggered by hostile encounters
- Initiative order determined by d20 rolls
- Attack rolls: d20 + attack bonus vs enemy AC
- Damage applied to HP, tracked in state
- Party members act in character during combat
- Enemy behavior defined in bestiary lore

### 4.10 Quest System
- Main quest: "Find the Starwell Relic" — multi-stage with branching outcomes
- Side quests: unlocked by player choices and world flags
- Quest journal updated after each relevant turn
- Quest completion tracked in world_flags

### 4.11 Human-in-the-Loop Confirmation
- Required for irreversible actions: character death, betraying the party, destroying artifacts
- GM pauses stream and presents a confirmation prompt before resolving
- Player must explicitly confirm or reconsider

### 4.12 Agent Telemetry Dashboard
- Toggle-able panel in the frontend (off for players, on for demo/dev mode)
- Shows per-turn: which agents were called, in what order, tool calls made, latency per agent
- Rendered as a Gantt-style horizontal timeline
- Displays raw agent messages ("Warrior said: I'll take point...")
- Data sourced from the OpenTelemetry trace summary returned with each turn response

---

## 5. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Time to first streamed token | < 5 seconds P90 |
| Full narration visible | < 8 seconds P90 |
| Agent response latency (parallel) | < 4 seconds (slowest agent) |
| Cosmos DB point read | < 10ms P99 |
| Cosmos DB point write | < 15ms P99 |
| IQ retrieval | < 400ms |
| Uptime | 99.5% for demo/hackathon window |
| Max concurrent sessions | 10 (hackathon scope) |
| Knowledge base size | ~50 documents, ~25,000 tokens total |
| Session isolation | 100% — no cross-session data access possible |

---

## 6. User Stories

### Player Stories

**US-01** — As a player, I want to describe my action in plain English so that I don't need to learn game syntax.

**US-02** — As a player, I want to see my party members react to events in character so that the world feels alive.

**US-03** — As a player, I want dice rolls shown with context so that I understand why I succeeded or failed.

**US-04** — As a player, I want a quest journal so that I can track my objectives and discovered clues.

**US-05** — As a player, I want to resume my adventure after closing the app so that I don't lose progress.

**US-06** — As a player, I want the GM to present choices so that I know my options without having to guess.

**US-07** — As a player, I want the game to warn me before irreversible decisions so that I don't accidentally wreck my campaign.

**US-08** — As a player, I want narration to appear word by word so that the game feels alive rather than making me wait for a full response.

**US-09** — As a player, I want my save to be private so that other users cannot access or corrupt my campaign.

### GM Agent Stories

**US-10** — As the GM agent, I want to query Foundry IQ in parallel with agent calls so that lore retrieval does not add to total latency.

**US-11** — As the GM agent, I want to invoke all required character agents simultaneously so that total turn time equals the slowest agent, not the sum.

**US-12** — As the GM agent, I want to resolve all rolls via Code Interpreter so that outcomes are deterministic and auditable.

**US-13** — As the GM agent, I want to start streaming my narration as soon as I have agent responses so that the player sees output quickly.

**US-14** — As the GM agent, I want to emit an OpenTelemetry span for every operation so that the full turn trace is visible in App Insights.

**US-15** — As the GM agent, I want to validate the player's JWT before touching any state so that no unauthenticated request can affect a campaign.

### Character Agent Stories

**US-16** — As the Warrior agent, I want to react to danger with bold tactical suggestions in character.

**US-17** — As the Mage agent, I want to query Foundry IQ for lore about magical artifacts and ruins.

**US-18** — As the Rogue agent, I want to request stealth checks when the party approaches guarded areas.

**US-19** — As the Healer agent, I want to flag ethical concerns when the party considers destructive actions.

**US-20** — As the Rival agent, I want to pursue my own agenda and create dramatic tension without breaking the game.

---

## 7. Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     React Frontend                       │
│  Auth (MSAL) | SSE Stream | Character Sheets | Telemetry │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTPS + JWT  (SSE response)
┌────────────────────────▼─────────────────────────────────┐
│            Game Master Agent (Hosted Agent)              │
│  1. Validate JWT → resolve session_id                    │
│  2. Read state (Cosmos, point read)                      │
│  3. Fire IQ query + all agent calls IN PARALLEL          │
│  4. Resolve rolls (Code Interpreter)                     │
│  5. STREAM narration via SSE                             │
│  6. Write state (Cosmos, non-blocking)                   │
└──┬──────────┬──────────┬──────────┬───────────────────── ┘
   │          │          │          │          (parallel)
┌──▼──┐  ┌───▼──┐  ┌────▼─┐  ┌────▼──┐  ┌─────────┐
│Warr-│  │Mage  │  │Rogue │  │Healer│  │ Rival   │
│ior  │  │Agent │  │Agent │  │Agent │  │ Agent   │
└─────┘  └──────┘  └──────┘  └──────┘  └─────────┘
                         │
         ┌───────────────┼──────────────┬──────────────┐
         │               │              │              │
┌────────▼─────┐ ┌───────▼──────┐ ┌────▼───────┐ ┌───▼──────────┐
│  Foundry IQ  │ │   Cosmos DB  │ │    Code    │ │  App Insights│
│  World Lore  │ │  (2 containers│ │Interpreter │ │  OTel Traces │
│              │ │ users/sessions│ │Dice / Math │ │              │
└──────────────┘ └──────────────┘ └────────────┘ └──────────────┘
```

---

## 8. Authentication Architecture

### Entra External ID Flow

```
Player → MSAL login popup → Entra External ID tenant
       ← JWT (contains user_id = Entra object ID)

Player → POST /turn  (Authorization: Bearer <jwt>)
       → GM validates JWT via Entra JWKS endpoint
       → GM looks up users container: user_id → session_id
       → GM verifies sessions container: session.user_id == jwt.user_id
       → Turn processes only if both checks pass
```

### Session Isolation Guarantee

Cosmos DB is partitioned by `session_id`. There is no query that returns records
across partitions. A player with a valid JWT for user A has no path to read or write
user B's session, because:
- They cannot know user B's `session_id` (a private UUID)
- Even if they guessed it, the GM enforces `session.user_id == jwt.user_id`
- Cosmos RBAC is scoped to the managed identity, not the player JWT

---

## 9. Latency Design

### Why Parallelization Is Required

Sequential agent invocation at 3s per agent:
- 3 agents × 3s = **9s minimum** — exceeds the 8s P90 target

Parallel agent invocation:
- 3 agents simultaneously = **~3–4s** (slowest agent determines total)
- Combined with streaming: first token visible at **~4–5s**

### Turn Latency Breakdown

| Phase | Duration | Notes |
|---|---|---|
| JWT validation | ~5ms | Cached JWKS |
| Cosmos state read | ~10ms | Point read by session_id |
| IQ query + agent calls | ~3–4s | Fully parallel |
| Roll resolution | ~200ms | After agents return |
| First streamed token | ~1s | GM synthesis starts |
| **Time to first token** | **~4–5s** | Player sees text appearing |
| Full narration | ~3s streaming | Word by word |
| Cosmos state write | ~15ms | Non-blocking, fires after stream starts |

### Streaming UX States

| Time | What player sees |
|---|---|
| 0s | Action submitted, input disabled |
| 0–4s | "The party deliberates..." animated indicator |
| ~4s | First words of narration appear and stream |
| ~7s | Narration complete, choices and dice results appear |
| ~7s | Telemetry panel updates with full trace |

---

## 10. Distributed Tracing

### What Is Traced

Every turn produces one distributed trace in Azure Application Insights:

- Every agent invocation (name, duration, success/fail)
- Every tool call within each agent (IQ search, Code Interpreter, Cosmos read/write)
- GM synthesis duration
- Total turn duration

### Trace Propagation

The GM opens a root span at the start of each turn and injects the OpenTelemetry
trace context into every agent invocation header. Character agents emit child spans
automatically. The full tree is stitched together in App Insights without any
manual correlation.

### Frontend Telemetry Panel

The GM returns a `trace_summary` object with every completed turn:

```json
{
  "turn": 14,
  "trace_id": "abc123",
  "total_ms": 6840,
  "spans": [
    { "name": "gm.iq_query",       "ms": 310  },
    { "name": "warrior.invoke",    "ms": 2900 },
    { "name": "mage.invoke",       "ms": 3200 },
    { "name": "rogue.invoke",      "ms": 2700 },
    { "name": "gm.roll_resolution","ms": 190  },
    { "name": "gm.synthesis",      "ms": 3100 }
  ],
  "agent_messages": {
    "warrior": "I'll take point. Something feels wrong about this gate.",
    "mage": "The sigil matches the description in the Veylin codex.",
    "rogue": "I'll check for traps. Give me thirty seconds."
  }
}
```

Rendered as a Gantt timeline in `AgentTelemetry.tsx`. Toggled by the player.

---

## 11. State Management

### Cosmos DB Design

Two containers, both using point reads/writes only:

**users** (partition: `user_id`)
- Maps Entra user_id → session_id
- Written once at character creation; read once per turn for session resolution

**sessions** (partition: `session_id`)
- Full `CampaignState` JSON document per player
- Read at turn start; written at turn end (non-blocking, after stream starts)
- Includes `user_id` back-reference for ownership verification

### State Update Protocol

1. GM reads session state (point read, ~10ms)
2. GM processes turn (parallel agents, rolls, narration stream)
3. GM fires async write to Cosmos DB immediately after stream starts
4. If write succeeds: normal flow
5. If write fails: GM retries once synchronously, then returns `state_warning: true` in done event

### History Summarization

To prevent context window overflow on long campaigns:
- `recent_history` stores the last 5 turn summaries (rolling)
- Every 10 turns, the GM summarizes the oldest 5 turns into one paragraph
- The paragraph replaces those 5 entries
- Full turn traces are stored separately in `last_trace` for the telemetry panel

---

## 12. Deployment Plan

### Phase 1 — Local Development
- Run all agents locally as Python processes
- Use mock Foundry IQ (local markdown search with basic keyword matching)
- SQLite for state persistence
- Validate game loop, agent behavior, parallelization logic, and streaming

### Phase 2 — Azure Foundry Deployment
- Push agent containers to ACR
- Deploy each agent as a Hosted Agent in Foundry Agent Service
- Upload knowledge base to Foundry IQ index (`eldervale-campaign`)
- Provision Cosmos DB with two containers (users, sessions)
- Configure Entra External ID tenant and app registration
- Configure Entra managed identities for all agents
- Wire up environment variables and App Insights connection strings

### Phase 3 — Frontend + Integration
- Deploy React frontend to Azure Static Web Apps
- Integrate MSAL for Entra External ID login
- Connect frontend to GM SSE endpoint
- Implement streaming text rendering in AdventureLog
- Enable AgentTelemetry Gantt panel

### Phase 4 — Hardening
- Add evaluation suite (story consistency + rules correctness + personality)
- Add auth + session isolation integration tests
- Configure Azure Monitor dashboards (latency, agent call counts, error rates)
- Load test to 10 concurrent sessions
- Add human-in-the-loop confirmation flows

---

## 13. Out of Scope (v1)

- Voice input / text-to-speech
- Image generation (character portraits, maps)
- Multiplayer (multiple human players simultaneously)
- Mobile native app
- Leveling system beyond quest completion
- Persistent economy (gold, trading)
- Map visualization

---

## 14. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GM loses narrative coherence over long sessions | Medium | High | Rolling 5-turn summary; inject into context every turn |
| Character agents break personality | Medium | Medium | Strict system prompts; personality eval suite |
| Foundry IQ returns irrelevant lore | Low | Medium | Tune chunk size (512 tokens); specific multi-term queries |
| State write failure mid-turn | Low | High | Async retry once; surface `state_warning` flag to player |
| Agent invocation latency exceeds 8s | Medium | High | Parallel asyncio.gather(); streaming hides remaining latency |
| Slowest agent becomes bottleneck | Low | Medium | Set 5s timeout per agent; GM uses partial results if one times out |
| JWT spoofing / session hijacking | Low | Critical | Validate JWT signature via Entra JWKS; verify user_id ownership on every turn |
| Player input causes harmful content | Low | High | Input validation layer; GM system prompt content guardrails |
| Cosmos cross-session leak | Very Low | Critical | Point reads only by partition key; user_id ownership check in GM |

---

## 15. Success Metrics

| Metric | Target |
|---|---|
| Time to first streamed token P90 | < 5 seconds |
| Full narration visible P90 | < 8 seconds |
| Story consistency score (eval suite) | > 90% |
| Rules correctness score (eval suite) | > 95% |
| Agent personality adherence (eval suite) | > 85% |
| State persistence reliability | 99.9% |
| Session isolation (auth tests) | 100% |
| Player session length (avg) | > 10 turns |

---

## 16. Synthetic World — Eldervale

### Setting Summary

Eldervale is a fractured kingdom where the moon shattered three centuries ago. Magic is unstable,
the old roads are haunted, and five factions compete to claim the Starwell Relics — artifacts that
may restore or permanently destroy what remains of the sky. The tone is dark, curious, and morally complex.

### Central Conflict

The Starwell Relic buried beneath the Moonlit Gate could seal the fractures in the sky — or tear
them open permanently. The player's party must find it before Kael Thorn does, while navigating
the competing agendas of the Iron Compact, the Order of the Silver Root, and the Hollow Court.

### Main Quest Stages

1. **The Ruined Chapel** — Discover the eye sigil and connect it to the Moonlit Gate
2. **The Moonlit Gate** — Speak the three conflicting truths to open the gate
3. **The Memory Vault** — Navigate the pre-shatter kingdom and recover the Relic
4. **The Reckoning** — Decide what to do with the Relic (multiple endings)

---

## 17. Definition of Done

A turn is complete when:
- [ ] JWT validated and user_id → session_id resolved
- [ ] session.user_id verified against jwt.user_id
- [ ] CampaignState read from Cosmos DB (point read)
- [ ] OpenTelemetry turn span opened
- [ ] Foundry IQ query fired in parallel with agent invocations
- [ ] All required character agents invoked simultaneously via asyncio.gather()
- [ ] Trace context propagated to all agent invocations
- [ ] All dice roll requests resolved via Code Interpreter
- [ ] GM synthesis stream started — first SSE token sent to frontend
- [ ] CampaignState written to Cosmos DB (non-blocking, after stream starts)
- [ ] SSE stream closed with choices, roll results, and trace_summary
- [ ] No agent has broken character or surfaced a GM-only secret
- [ ] AgentTelemetry panel data available in the done event
