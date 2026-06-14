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
| State persistence | Foundry Agent Service managed storage + Azure Cosmos DB |
| Dice / combat math | Code Interpreter tool (Foundry built-in) |
| Web inspiration | Bing Grounding / Web Search tool (Foundry built-in) |
| Observability | Azure Monitor + Foundry telemetry |
| Container registry | Azure Container Registry (ACR) |
| Identity | Microsoft Entra ID (managed agent identity per agent) |
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
│   └── foundry_client.py            # Foundry Agent Service SDK wrapper
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
│   │   ├── components/
│   │   │   ├── AdventureLog.tsx
│   │   │   ├── CharacterSheet.tsx
│   │   │   ├── DiceRoll.tsx
│   │   │   ├── QuestJournal.tsx
│   │   │   └── AgentTelemetry.tsx
│   │   └── api/
│   │       └── foundryClient.ts
│   └── package.json
│
├── infra/
│   ├── main.bicep                   # Azure infrastructure as code
│   ├── agents.bicep                 # Hosted agent definitions
│   ├── cosmos.bicep                 # State database
│   └── acr.bicep                   # Container registry
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

1. Receives player input via the frontend API
2. Reads current campaign state from storage
3. Queries Foundry IQ for relevant lore (location, quest, NPCs)
4. Decides which character agents to invoke and in what order
5. Calls character agents via Foundry Agent Service endpoints
6. Uses Code Interpreter to resolve dice rolls and combat math
7. Synthesizes all responses into a final narrated scene
8. Updates campaign state in storage
9. Returns scene + choices to the player

**Tools available to GM:**
- `foundry_iq_search` — retrieve world lore
- `code_interpreter` — dice rolls, combat resolution
- `web_search` — public-domain inspiration only
- `storage_read` / `storage_write` — campaign state
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
| Rogue | code_interpreter (stealth/trap rolls), storage_read (contacts/secrets) |
| Healer | foundry_iq_search (religion/healing lore), code_interpreter (medicine rolls) |
| Rival | foundry_iq_search, storage_read (world flags) |

---

## Shared State Schema

Every agent call passes the current `CampaignState`. The GM is responsible for updating it after each turn.

```python
# shared/state_schema.py

from pydantic import BaseModel
from typing import List, Dict, Optional

class CharacterState(BaseModel):
    agent: str
    name: str
    health: int
    max_health: int
    inventory: List[str]
    conditions: List[str]
    trust_level: Optional[str]  # for rival

class CampaignState(BaseModel):
    campaign: str
    location: str
    active_quest: str
    turn: int
    party: List[CharacterState]
    world_flags: Dict[str, any]
    quest_log: List[str]
    recent_history: List[str]  # last 5 turns summary
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
# Using Azure AI Foundry CLI
az ai foundry iq upload \
  --index eldervale-campaign \
  --source ./knowledge/ \
  --chunk-size 512 \
  --overlap 64
```

### GM Query Pattern

```python
# In GM agent, before narrating a scene
lore_results = await foundry_iq.search(
    index="eldervale-campaign",
    query=f"{current_location} {active_quest} {relevant_npc}",
    top_k=3
)
```

### Knowledge Document Format

Every knowledge file must follow this structure for optimal retrieval:

```markdown
# [Entity Name]

**Type:** [Location | Faction | Character | Quest | Item | Monster]
**Tags:** tag1, tag2, tag3

## Summary
One paragraph overview.

## Known Facts
- Fact players can discover
- Another known fact

## Secrets
- [GM ONLY] Secret the players don't know yet

## Related Entities
- EntityName1
- EntityName2
```

---

## Hosted Agent Deployment

Each agent is containerized and deployed independently.

### Container Pattern

```dockerfile
# agents/game_master/Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "agent.py"]
```

### Deployment via Bicep

```bicep
// infra/agents.bicep
resource gameMasterAgent 'Microsoft.AI/agents@2024-01-01' = {
  name: 'game-master-agent'
  properties: {
    image: '${acr.loginServer}/game-master:latest'
    identity: { type: 'SystemAssigned' }
    tools: ['code_interpreter', 'foundry_iq', 'web_search']
    storageConnection: cosmosDb.connectionString
  }
}
```

### Agent Invocation Pattern (GM calling character agents)

```python
# shared/foundry_client.py
from azure.ai.foundry import AgentClient

async def invoke_character_agent(agent_id: str, context: dict) -> dict:
    client = AgentClient(endpoint=FOUNDRY_ENDPOINT)
    response = await client.invoke(
        agent_id=agent_id,
        messages=[{"role": "user", "content": json.dumps(context)}]
    )
    return json.loads(response.content)
```

---

## Game Loop (Turn by Turn)

```
1. Player sends input → Frontend → GM Agent endpoint
2. GM reads CampaignState from storage
3. GM queries Foundry IQ for scene-relevant lore
4. GM determines which agents to invoke (1–4 typically)
5. GM invokes each character agent in sequence with shared context
6. Character agents return { speech, action, roll_request }
7. GM executes any roll_requests via Code Interpreter
8. GM synthesizes scene narrative
9. GM updates CampaignState in storage
10. GM returns { scene, choices, rolls, state_delta } to frontend
11. Frontend renders scene, updates character sheets
```

---

## Rules Engine

Lightweight rules in `shared/rules.py`:

- Ability checks: d20 + modifier vs difficulty class (DC)
- Attack rolls: d20 + attack bonus vs armor class (AC)
- Saving throws: d20 + save modifier vs effect DC
- Health: tracked per character, reduced by damage, restored by healing
- Inventory: max 10 items per character
- Conditions: poisoned, stunned, blessed, cursed, etc.
- Relationships: trust_level for rival (hostile → uncertain → neutral → ally)
- Quest progress: flags in world_flags dict

---

## Frontend Requirements

The React frontend must display:

- **Adventure Log** — scrolling scene narrative with GM text highlighted
- **Character Sheets** — health bars, inventory, conditions for each party member
- **Dice Roll Visualizer** — animated roll display when checks occur
- **Quest Journal** — active and completed quests with clue tracking
- **Agent Telemetry Panel** — (dev mode) shows which agents were called, latency, tool calls
- **Player Input** — text field + submit, with suggested quick actions

---

## Environment Variables

```bash
FOUNDRY_ENDPOINT=https://<your-foundry-endpoint>.azure.com
FOUNDRY_API_KEY=<managed via Entra ID, not hardcoded>
FOUNDRY_IQ_INDEX=eldervale-campaign
COSMOS_DB_CONNECTION=<connection string>
ACR_LOGIN_SERVER=<registry>.azurecr.io
GAME_MASTER_AGENT_ID=<agent-id>
WARRIOR_AGENT_ID=<agent-id>
MAGE_AGENT_ID=<agent-id>
ROGUE_AGENT_ID=<agent-id>
HEALER_AGENT_ID=<agent-id>
RIVAL_AGENT_ID=<agent-id>
```

Never hardcode credentials. Use Entra ID managed identity in production.

---

## Testing

### Story Consistency Evals
- Input: sequence of player actions
- Expected: narrative stays internally consistent, world flags update correctly
- Assert: location names match IQ lore, character names are stable

### Rules Correctness Evals
- Input: structured combat scenario
- Expected: correct dice math, correct HP deduction
- Assert: roll results match Code Interpreter output

### Agent Personality Evals
- Input: emotional scene prompt per agent
- Expected: response matches defined personality traits
- Assert: Warrior doesn't cast spells, Mage doesn't intimidate

---

## Key Constraints

- The GM is the ONLY agent that calls other agents
- Character agents NEVER communicate directly with each other
- Character agents NEVER break the fourth wall
- Dice rolls ALWAYS go through Code Interpreter, never ad-hoc text
- State ALWAYS persists to Cosmos DB before returning a response
- Foundry IQ is the source of truth for world lore — agents must not invent facts
- Secrets in knowledge files are NEVER returned to the player directly
- Human-in-the-loop confirmation required for irreversible actions (death, major quest failures)
