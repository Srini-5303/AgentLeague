"""Local StateStore backed by SQLite.

Mirrors the Cosmos design: two logical "containers" (users keyed by user_id,
sessions keyed by session_id) accessed only by point read/write. Async wrapper
runs the blocking sqlite calls in a thread so it shares the StateStore async API
with the Cosmos implementation.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Optional

from shared.interfaces.state import StateStore
from shared.state_schema import CampaignState, UserRecord


class SQLiteStateStore(StateStore):
    def __init__(self, path: str):
        self._path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as c:
            c.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, doc TEXT)")
            c.execute("CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, doc TEXT)")

    # ── users (partition: user_id) ──────────────────────────────────────
    async def get_user(self, user_id: str) -> Optional[UserRecord]:
        def _read():
            with self._connect() as c:
                row = c.execute("SELECT doc FROM users WHERE user_id = ?", (user_id,)).fetchone()
                return UserRecord.model_validate_json(row["doc"]) if row else None
        return await asyncio.to_thread(_read)

    async def create_user(self, user: UserRecord) -> None:
        def _write():
            with self._connect() as c:
                c.execute(
                    "INSERT OR REPLACE INTO users (user_id, doc) VALUES (?, ?)",
                    (user.id, user.model_dump_json()),
                )
        await asyncio.to_thread(_write)

    # ── sessions (partition: session_id) ────────────────────────────────
    async def get_session(self, session_id: str) -> Optional[CampaignState]:
        def _read():
            with self._connect() as c:
                row = c.execute(
                    "SELECT doc FROM sessions WHERE session_id = ?", (session_id,)
                ).fetchone()
                return CampaignState.model_validate_json(row["doc"]) if row else None
        return await asyncio.to_thread(_read)

    async def write_session(self, state: CampaignState) -> None:
        def _write():
            with self._connect() as c:
                c.execute(
                    "INSERT OR REPLACE INTO sessions (session_id, doc) VALUES (?, ?)",
                    (state.session_id, state.model_dump_json()),
                )
        await asyncio.to_thread(_write)

    async def delete_user(self, user_id: str) -> None:
        def _del():
            with self._connect() as c:
                c.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        await asyncio.to_thread(_del)

    async def delete_session(self, session_id: str) -> None:
        def _del():
            with self._connect() as c:
                c.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        await asyncio.to_thread(_del)

    async def close(self) -> None:
        return None
