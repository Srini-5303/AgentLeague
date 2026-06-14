"""Local AuthProvider.

Two modes (Settings.dev_auth_bypass):
  - bypass=True : any request (even no token) maps to DEV_USER_ID. Frictionless dev.
  - bypass=False: validates an HS256 token signed with DEV_AUTH_SECRET, returning
    its `sub`. Lets you exercise the real validate→user_id path and multi-user
    isolation tests without standing up Entra. Mint tokens with mint_dev_token().
"""
from __future__ import annotations

import jwt

from shared.config import Settings
from shared.interfaces.auth import AuthError, AuthProvider


class DevAuthProvider(AuthProvider):
    def __init__(self, settings: Settings):
        self._s = settings

    async def validate(self, bearer_token: str | None) -> str:
        if self._s.dev_auth_bypass:
            return self._s.dev_user_id
        if not bearer_token:
            raise AuthError("missing bearer token")
        token = bearer_token.removeprefix("Bearer ").strip()
        try:
            payload = jwt.decode(token, self._s.dev_auth_secret, algorithms=["HS256"])
        except jwt.PyJWTError as e:
            raise AuthError(f"invalid token: {e}") from e
        user_id = payload.get("sub")
        if not user_id:
            raise AuthError("token missing sub")
        return user_id


def mint_dev_token(user_id: str, secret: str) -> str:
    """Helper for tests / the seed script — sign a dev token for a given user."""
    return jwt.encode({"sub": user_id}, secret, algorithm="HS256")
