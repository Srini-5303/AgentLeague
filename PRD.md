# PRD — Fantasy RPG Multi-Agent System
## Product Requirements Document

**Version:** 1.0  
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

This system solves all four problems with a true multi-agent architecture, Foundry IQ lore grounding, Code Interpreter for deterministic rules, and persistent state via Foundry Agent Service.

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

### 4.1 Character Creation
- Player names their character and picks a class (Fighter, Wizard, Ranger, Cleric, or custom)
- System generates starting stats, inventory, and a brief backstory hook
- Player's character is tracked alongside AI party members in shared state

### 4.2 Game Master Orchestration
- GM agent receives every player input
- GM decides which character agents to activate per turn (1–4 per scene)
- GM queries Foundry IQ for lore before narrating important scenes
- GM uses Code Interpreter to resolve all dice rolls
- GM updates and persists campaign state after every turn
- GM narrates the final scene in rich prose
- GM presents 3–4 player choices at the end of each turn

### 4.3 AI Character Agents
Five persistent character agents, each deployed as a Hosted Agent:

| Agent | Name | Role | Personality |
|---|---|---|---|
| Warrior | Bran Ironvale | Frontline protector | Brave, direct, suspicious of magic |
| Mage | Lyra Vey | Arcane scholar | Curious, analytical, slightly arrogant |
| Rogue | Sable Dusk | Scout and trickster | Witty, skeptical, opportunistic |
| Healer | Mirra of the Root | Support and moral compass | Compassionate, principled, observant |
| Rival | Kael Thorn | Recurring story antagonist/ally | Charismatic, proud, unpredictable |

Each agent:
- Speaks in character with a consistent voice
- Reacts to story events based on their backstory
- Has defined tool access based on their role
- Returns structured responses the GM can parse and synthesize

### 4.4 Dice Roll System
- All checks use d20 + modifier vs difficulty class
- Outcomes: success, partial success, failure
- Rolls are executed by Code Interpreter — deterministic, auditable
- Roll results displayed to the player with context

### 4.5 World Lore (Foundry IQ)
- Campaign world "Eldervale" stored as a structured knowledge base in Foundry IQ
- Covers: world overview, 5+ locations, 3 factions, character backstories, 3 quests, 5 artifacts, 5 monsters, homebrew rules
- GM retrieves relevant lore before narrating each scene
- Secrets in lore are marked GM-only and never surfaced directly to the player

### 4.6 Persistent Campaign State
- Full campaign state persisted to Cosmos DB after every turn
- State includes: location, active quest, party health/inventory/conditions, world flags, quest log, session summary
- State survives session restarts — player can resume where they left off

### 4.7 Combat System
- Turn-based combat triggered by hostile encounters
- Initiative order determined by d20 rolls
- Attack rolls: d20 + attack bonus vs enemy AC
- Damage applied to HP, tracked in state
- Party members act in character during combat (Warrior attacks, Mage casts, Healer heals)
- Enemy behavior defined in bestiary lore

### 4.8 Quest System
- Main quest: "Find the Starwell Relic" — multi-stage with branching outcomes
- Side quests: unlocked by player choices and world flags
- Quest journal updated after each relevant turn
- Quest completion tracked in world_flags

### 4.9 Human-in-the-Loop Confirmation
- Required for irreversible actions: character death, betraying the party, destroying artifacts
- GM pauses and presents a confirmation prompt before resolving
- Player must explicitly confirm or reconsider

### 4.10 Agent Telemetry Dashboard
- Dev/demo mode panel in the frontend
- Shows per-turn: which agents were called, in what order, tool calls made, latency per agent
- Visualizes the multi-agent flow in real time

---

## 5. Non-Functional Requirements

| Requirement | Target |
|---|---|
| Response latency (full turn) | < 8 seconds P90 |
| Agent response latency | < 3 seconds per agent |
| State persistence | < 500ms write to Cosmos DB |
| IQ retrieval | < 1 second per query |
| Uptime | 99.5% for demo/hackathon window |
| Max concurrent sessions | 10 (hackathon scope) |
| Knowledge base size | ~50 documents, ~25,000 tokens total |

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

### GM Agent Stories

**US-08** — As the GM agent, I want to query Foundry IQ before narrating so that I stay consistent with campaign lore.

**US-09** — As the GM agent, I want to invoke only the relevant character agents per scene so that responses are fast and focused.

**US-10** — As the GM agent, I want to resolve all rolls via Code Interpreter so that outcomes are deterministic and auditable.

**US-11** — As the GM agent, I want to persist state before returning a response so that progress is never lost.

### Character Agent Stories

**US-12** — As the Warrior agent, I want to react to danger with bold tactical suggestions in character.

**US-13** — As the Mage agent, I want to query Foundry IQ for lore about magical artifacts and ruins.

**US-14** — As the Rogue agent, I want to request stealth checks when the party approaches guarded areas.

**US-15** — As the Healer agent, I want to flag ethical concerns when the party considers destructive actions.

**US-16** — As the Rival agent, I want to pursue my own agenda and create dramatic tension without breaking the game.

---

## 7. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   React Frontend                    │
│  Adventure Log | Character Sheets | Dice | Telemetry│
└───────────────────────┬─────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼─────────────────────────────┐
│           Game Master Agent (Hosted Agent)          │
│  Orchestrator + Narrator + World Builder            │
│  Tools: Foundry IQ, Code Interpreter, Web Search    │
│         Storage R/W, Agent Invocation               │
└──┬──────────┬──────────┬──────────┬─────────────────┘
   │          │          │          │
┌──▼──┐  ┌───▼──┐  ┌────▼─┐  ┌────▼──┐  ┌─────────┐
│Warr-│  │Mage  │  │Rogue │  │Healer│  │ Rival   │
│ior  │  │Agent │  │Agent │  │Agent │  │ Agent   │
│Agent│  │      │  │      │  │      │  │         │
└─────┘  └──────┘  └──────┘  └──────┘  └─────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────────┐
│  Foundry IQ  │ │   Cosmos DB  │ │Code Interpreter│
│  World Lore  │ │Campaign State│ │  Dice / Math   │
└──────────────┘ └─────────────┘ └────────────────┘
```

---

## 8. Foundry IQ Knowledge Base

### Index Name
`eldervale-campaign`

### Document Set

| File | Records | Purpose |
|---|---|---|
| world_overview.md | 1 | Setting, tone, laws of magic, factions at a glance |
| locations.md | 5+ | Villages, ruins, dungeons, temples, roads |
| factions.md | 3 | Motivations, leaders, alliances, secrets |
| characters.md | 6 | All 5 party agents + rival + key NPCs |
| quests.md | 3 | Main quest + 2 side quests with clues and twists |
| items_and_artifacts.md | 5 | Relics, weapons, cursed items |
| bestiary.md | 5 | Monsters with behavior, weaknesses, encounter difficulty |
| homebrew_rules.md | 1 | Dice system, combat, rests, inventory, leveling |
| session_notes_template.md | 1 | Template for per-session state summaries |

### Retrieval Pattern

GM queries IQ at the start of each turn with:
- Current location name
- Active quest name  
- Any NPC or artifact mentioned in player input

Top 3 results are injected into GM context before agent invocation.

---

## 9. State Management

### Storage Architecture

- **Hot state** (current turn): held in GM agent memory during turn processing
- **Warm state** (campaign): persisted to Cosmos DB after every turn
- **Cold state** (session history): archived session summaries for long campaigns

### State Update Protocol

1. GM reads state at start of turn
2. GM processes turn (agent calls, rolls, narration)
3. GM writes updated state to Cosmos DB
4. GM returns response to frontend
5. If write fails: GM retries once, then returns response with `state_warning` flag

---

## 10. Deployment Plan

### Phase 1 — Local Development
- Run all agents locally as Python processes
- Use mock Foundry IQ (local markdown search)
- SQLite for state persistence
- Validate game loop and agent behavior

### Phase 2 — Azure Foundry Deployment
- Push agent containers to ACR
- Deploy each agent as a Hosted Agent in Foundry Agent Service
- Upload knowledge base to Foundry IQ index
- Provision Cosmos DB for state
- Configure Entra ID managed identities
- Wire up environment variables

### Phase 3 — Frontend + Integration
- Deploy React frontend to Azure Static Web Apps
- Connect frontend to GM Agent endpoint
- Enable telemetry panel for demo

### Phase 4 — Hardening
- Add evaluation suite (story consistency + rules correctness)
- Add Azure Monitor dashboards
- Load test to 10 concurrent sessions
- Add human-in-the-loop confirmation flows

---

## 11. Out of Scope (v1)

- Voice input / text-to-speech
- Image generation (character portraits, maps)
- Multiplayer (multiple human players simultaneously)
- Mobile native app
- Leveling system beyond quest completion
- Persistent economy (gold, trading)
- Map visualization

---

## 12. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GM agent loses narrative coherence over long sessions | Medium | High | Summarize history every 5 turns; inject summary into context |
| Character agents break personality | Medium | Medium | Strict system prompts; personality eval suite |
| Foundry IQ returns irrelevant lore | Low | Medium | Tune chunk size (512 tokens); use specific query terms |
| State write failure mid-turn | Low | High | Retry logic; surface warning to player; idempotent writes |
| Agent invocation latency exceeds 8s | Medium | High | Parallelize non-dependent agent calls with async |
| Player input causes harmful content | Low | High | Input validation layer; GM system prompt content guardrails |

---

## 13. Success Metrics

| Metric | Target |
|---|---|
| Story consistency score (eval suite) | > 90% |
| Rules correctness score (eval suite) | > 95% |
| Player session length (avg) | > 10 turns |
| Agent personality adherence (eval suite) | > 85% |
| Turn response time P90 | < 8 seconds |
| State persistence reliability | 99.9% |

---

## 14. Synthetic World — Eldervale

### Setting Summary

Eldervale is a fractured kingdom where the moon shattered three centuries ago. Magic is unstable, the old roads are haunted, and five factions compete to claim the Starwell Relics — artifacts that may restore or permanently destroy what remains of the sky. The tone is dark, curious, and morally complex.

### Central Conflict

The Starwell Relic buried beneath the Moonlit Gate could seal the fractures in the sky — or tear them open permanently. The player's party must find it before Kael Thorn does, while navigating the competing agendas of the Iron Compact, the Order of the Silver Root, and the Hollow Court.

### Main Quest Stages

1. **The Ruined Chapel** — Discover the eye sigil and connect it to the Moonlit Gate
2. **The Moonlit Gate** — Speak the three conflicting truths to open the gate
3. **The Memory Vault** — Navigate the pre-shatter kingdom and recover the Relic
4. **The Reckoning** — Decide what to do with the Relic (multiple endings)

---

## 15. Definition of Done

A turn is complete when:
- [ ] GM has read current CampaignState
- [ ] GM has queried Foundry IQ for relevant lore
- [ ] All relevant character agents have responded
- [ ] All requested dice rolls have been resolved via Code Interpreter
- [ ] A narrated scene has been produced
- [ ] CampaignState has been written to Cosmos DB
- [ ] The frontend has received `{ scene, choices, rolls, state_delta }`
- [ ] No agent has broken character or surfaced a GM-only secret
