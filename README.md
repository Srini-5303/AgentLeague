# Eldervale — A Multi-Agent Norse RPG on Azure AI Foundry

A text adventure where every party member is a live AI agent, orchestrated by a
Game Master, set in **Eldervale** — a fantastical-but-grounded Norse world whose
central catastrophe (the shattering of the moon Máni) is the in-world reading of
the real **SN 1054 "guest star"** supernova.

Built **local-first**: the entire game runs on your laptop with no cloud and no
keys, then swaps to Azure AI Foundry / Cosmos DB / Entra **by changing config**,
because every external dependency sits behind an interface in `shared/` (the *seam*).

---

## Architecture at a glance

```
React + TS (Vite / Static Web Apps)
        │  HTTPS + JWT, SSE response
        ▼
GM Orchestrator — FastAPI (Azure Container Apps)      ← agents/game_master/
  auth → resolve+own session → HITL gate → select agents
       → PARALLEL(lore search + character agents, timeout-guarded)
       → resolve dice → STREAM narration (SSE) → write state → choices + trace
        │                         │                    │              │
   Character agents          Knowledge            State store      Tracer
   (system_prompt.md)        (Foundry IQ /        (Cosmos /        (App Insights /
   via Foundry models        local md search)     SQLite)          in-memory)
```

The GM runs as **our** FastAPI service (not a Foundry hosted agent) because SSE
streaming + true `asyncio.gather()` fan-out need a process we control, and Azure
Static Web Apps managed functions can't stream SSE.

The same `agents/<role>/system_prompt.md` files are the single source of truth for
personality in **both** runtimes.

---

## Run it locally (no cloud, no keys)

```powershell
./scripts/run_local.ps1          # creates venv, installs deps, copies .env, starts GM on :8000
```

In another terminal, drive a turn:

```powershell
.\.venv\Scripts\python.exe scripts\sse_smoke.py "I search the ruined chapel for ancient runes."
```

Run the frontend:

```powershell
cd frontend; npm install; npm run dev      # http://localhost:5173 (proxies /turn to :8000)
```

Defaults use `LLM_PROVIDER=mock` (canned, deterministic — proves the whole pipeline
offline). For real local narration set `LLM_PROVIDER` in `.env` to `openai`,
`azure_openai`, or `ollama` and add the matching key/endpoint.

Run the tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q   # 26 tests: dice, state, selection, auth-isolation, turn flow, HITL, secrets
```

---

## Configuration (the seam)

`RUNTIME=local|azure` plus provider switches select implementations in
`shared/factory.py`. See `.env.example` for every variable. Highlights:

| Concern | local | azure |
|---|---|---|
| LLM | mock / openai / azure_openai / ollama | Foundry project models |
| Knowledge | keyword search over `knowledge/*.md` | Foundry IQ / Azure AI Search |
| State | SQLite | Cosmos DB (point ops, managed identity) |
| Auth | dev token / bypass | Entra External ID (JWKS) |
| Tracing | in-memory summary | App Insights + the same summary |

---

## Deploy to Azure (Phase 5) — what YOU do by hand

Claude wrote the IaC (`infra/main.bicep`), Dockerfile, and scripts; these steps need
your portal/CLI + credentials. **Never hardcode secrets — managed identity + env only.**

1. **Foundry**: create a Foundry resource + project; deploy models (**gpt-4o-mini**
   for the 5 character agents, **gpt-4o** for the narrator). Copy the project endpoint.
   *(Optional, cosmetic)* `python infra/deploy_agents.py --endpoint <ep>` registers named
   agents for the portal/traces — verify the preview SDK names first.
2. **Foundry IQ / Azure AI Search**: create the index `eldervale-campaign` with fields
   `id, title, content, source, gm_only`; then
   `python infra/upload_knowledge.py --endpoint <search-ep> --index eldervale-campaign`.
3. **Provision infra**: `az deployment group create -g <rg> -f infra/main.bicep -p namePrefix=eldervale`
   (creates Cosmos serverless w/ `users`+`sessions`, ACR, App Insights, Container Apps env).
4. **Build & push** the GM image to ACR (linux/amd64), then redeploy `main.bicep` with
   `-p gmImage=<acr>.azurecr.io/eldervale-gm:latest foundryProjectEndpoint=<ep>`.
5. **Grant the GM's managed identity** the **Cosmos DB Built-in Data Contributor** role
   (data-plane RBAC): `az cosmosdb sql role assignment create ...` with the app's principalId.
6. **Entra External ID**: create the external tenant; register the SPA (redirect URIs)
   + API; create the sign-up/sign-in flow. Record tenant id, client id, and **which claim
   holds the user id** (`sub` vs `oid` — test a real token; set `ENTRA_USER_ID_CLAIM`).
7. **Frontend**: set `VITE_API_BASE` to the Container App URL and `VITE_AUTH=msal`
   (wire `@azure/msal-react` into `src/auth/useAuth.ts`); deploy to Static Web Apps.
8. **Confirm SSE** streams through the Container Apps ingress unbuffered (the app sends
   `X-Accel-Buffering: no` + keep-alive; verify end-to-end).

---

## Repository map

- `agents/game_master/` — orchestrator, FastAPI app, character/narrator calls, HITL, choices, state-update, summarize
- `agents/<role>/system_prompt.md` — personality source of truth (warrior/mage/rogue/healer/rival + GM)
- `shared/` — config, interfaces (the seam), local+azure impls, dice, rules, factory, schema, tracing
- `knowledge/` — the Norse-Eldervale world bible (world/locations/factions/characters/quests/items/bestiary/rules); `[GM ONLY]` secrets are filtered from the player path
- `frontend/` — React+TS: AdventureLog (streaming), CharacterSheet, DiceRoll, QuestJournal, AgentTelemetry (Gantt), HITL modal
- `infra/` — `main.bicep`, `deploy_agents.py`, `upload_knowledge.py`
- `tests/` — rules_correctness, agent_behavior, auth_isolation, story_consistency

---

## Key invariants (enforced + tested)

- JWT validated before any state/agent call; `session.user_id == jwt.user_id` every turn (403 otherwise).
- Cosmos/SQLite point ops only, partitioned by id — no cross-partition queries.
- Character agents run in parallel (`asyncio.gather`), each timeout-guarded → partial results never stall a turn.
- Dice are deterministic and seedable; the engine is the source of truth.
- GM narration streams token-by-token over SSE; state is written before the stream closes.
- `[GM ONLY]` lore never reaches the player or the character agents.
- Irreversible acts pause for human confirmation.
