from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from shared.state_schema import CampaignState, UserRecord


class StateStore(ABC):
    """Point read/write persistence for users and campaign sessions.

    Implementations MUST use point operations keyed by partition key only
    (user_id for users, session_id for sessions) — never cross-partition queries.
    """

    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[UserRecord]: ...

    @abstractmethod
    async def create_user(self, user: UserRecord) -> None: ...

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[CampaignState]: ...

    @abstractmethod
    async def write_session(self, state: CampaignState) -> None:
        """Persist campaign state. Should honor optimistic concurrency (etag) in
        Azure; locally a plain upsert is fine."""

    @abstractmethod
    async def delete_user(self, user_id: str) -> None:
        """Remove a user record (point delete by user_id). No-op if absent."""

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Remove a campaign session (point delete by session_id). No-op if absent."""

    @abstractmethod
    async def close(self) -> None: ...
