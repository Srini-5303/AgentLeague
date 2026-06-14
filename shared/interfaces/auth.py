from __future__ import annotations

from abc import ABC, abstractmethod


class AuthError(Exception):
    """Raised on invalid/missing credentials. Orchestrator maps this to HTTP 401."""


class AuthProvider(ABC):
    @abstractmethod
    async def validate(self, bearer_token: str | None) -> str:
        """Validate the token and return the user_id. Raise AuthError on failure."""
