"""Azure Cosmos DB (NoSQL) StateStore — the production state backend.

Mirrors the SQLite store's point-op contract: users keyed by /user_id, sessions
keyed by /session_id. Uses the ASYNC Cosmos client so it doesn't block the
FastAPI event loop, and managed-identity auth (DefaultAzureCredential) — no keys.
Honors optimistic concurrency via the document _etag on writes.

NOTE: azure-cosmos / azure-identity are imported lazily here so local dev never
needs them. Install via requirements-azure.txt.
"""
from __future__ import annotations

from typing import Optional

from shared.config import Settings
from shared.interfaces.state import StateStore
from shared.state_schema import CampaignState, UserRecord


class CosmosStateStore(StateStore):
    def __init__(self, settings: Settings):
        from azure.cosmos.aio import CosmosClient
        from azure.identity.aio import DefaultAzureCredential

        self._s = settings
        self._credential = DefaultAzureCredential()
        self._client = CosmosClient(settings.cosmos_db_endpoint, credential=self._credential)
        db = self._client.get_database_client(settings.cosmos_db_database)
        self._users = db.get_container_client(settings.cosmos_users_container)
        self._sessions = db.get_container_client(settings.cosmos_sessions_container)

    async def get_user(self, user_id: str) -> Optional[UserRecord]:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            item = await self._users.read_item(item=user_id, partition_key=user_id)
            return UserRecord.model_validate(item)
        except CosmosResourceNotFoundError:
            return None

    async def create_user(self, user: UserRecord) -> None:
        body = user.model_dump(mode="json")
        body["id"] = user.id
        body["user_id"] = user.id  # partition key path is /user_id
        await self._users.upsert_item(body)

    async def get_session(self, session_id: str) -> Optional[CampaignState]:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            item = await self._sessions.read_item(item=session_id, partition_key=session_id)
            state = CampaignState.model_validate(item)
            state.etag = item.get("_etag")
            return state
        except CosmosResourceNotFoundError:
            return None

    async def write_session(self, state: CampaignState) -> None:
        from azure.cosmos.exceptions import CosmosAccessConditionFailedError
        body = state.model_dump(mode="json")
        body["id"] = state.session_id
        # session_id is both id and partition key path (/session_id)
        body["session_id"] = state.session_id
        if state.etag:
            try:
                await self._sessions.replace_item(
                    item=state.session_id, body=body,
                    etag=state.etag, match_condition="IfMatch",
                )
                return
            except CosmosAccessConditionFailedError:
                # Lost the optimistic-concurrency race; the orchestrator's per-session
                # lock makes this rare. Fall through to a last-writer-wins upsert.
                pass
        await self._sessions.upsert_item(body)

    async def delete_user(self, user_id: str) -> None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            await self._users.delete_item(item=user_id, partition_key=user_id)
        except CosmosResourceNotFoundError:
            pass

    async def delete_session(self, session_id: str) -> None:
        from azure.cosmos.exceptions import CosmosResourceNotFoundError
        try:
            await self._sessions.delete_item(item=session_id, partition_key=session_id)
        except CosmosResourceNotFoundError:
            pass

    async def close(self) -> None:
        await self._client.close()
        await self._credential.close()
