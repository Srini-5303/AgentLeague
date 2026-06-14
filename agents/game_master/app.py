"""FastAPI entrypoint for the Game Master orchestrator service.

Exposes:
  POST /turn   — SSE stream of turn events (agent_start, token, dice, confirm, done, error)
  GET  /state  — current campaign state for the authenticated player (resume/UI)
  GET  /health — liveness

This is the process the plan runs on Azure Container Apps (NOT Static Web Apps,
which cannot stream SSE). Services are built once from the seam at startup.
"""
from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from agents.game_master.orchestrator import GameMaster
from shared.config import get_settings
from shared.factory import build_auth, build_knowledge, build_llm, build_state
from shared.interfaces.auth import AuthError
from shared.state_schema import TurnRequest

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # disable proxy buffering (nginx / Container Apps ingress)
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    app.state.settings = s
    app.state.gm = GameMaster(
        llm=build_llm(s),
        knowledge=build_knowledge(s),
        state=build_state(s),
        auth=build_auth(s),
        settings=s,
    )
    yield
    await app.state.gm.state.close()


app = FastAPI(title="Eldervale GM", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to the SWA origin in Phase 5
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok", "runtime": get_settings().runtime}


@app.post("/turn")
async def turn(req: TurnRequest, request: Request, authorization: str | None = Header(default=None)):
    gm: GameMaster = request.app.state.gm

    async def event_stream():
        # keep-alive comment so proxies flush headers immediately
        yield ": connected\n\n"
        async for event in gm.run_turn(authorization, req):
            yield _sse(event)

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.get("/state")
async def state(request: Request, authorization: str | None = Header(default=None)):
    gm: GameMaster = request.app.state.gm
    try:
        user_id = await gm.auth.validate(authorization)
    except AuthError as e:
        return JSONResponse({"message": str(e)}, status_code=401)
    campaign = await gm._resolve_session(user_id)
    if campaign.user_id != user_id:
        return JSONResponse({"message": "ownership mismatch"}, status_code=403)
    return campaign.model_dump()


@app.post("/reset")
async def reset(request: Request, authorization: str | None = Header(default=None)):
    """Delete the player's saved campaign and start a fresh one. Returns the new
    campaign state so the frontend can reattach without a reload."""
    gm: GameMaster = request.app.state.gm
    try:
        campaign = await gm.reset_session(authorization)
    except AuthError as e:
        return JSONResponse({"message": str(e)}, status_code=401)
    return campaign.model_dump()
