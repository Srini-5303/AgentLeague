"""Microsoft Entra External ID JWT validation.

Validates the bearer token's RS256 signature against the tenant JWKS, checks the
audience, and returns the user id from the configured claim. Entra External ID
OIDC tokens commonly carry the user object id in `sub` (sometimes `oid`) — the
claim is configurable (ENTRA_USER_ID_CLAIM) and MUST be verified against a real
token during setup. JWKS keys are cached by PyJWKClient.

azure deps are not required here (only PyJWT, which is in core requirements), but
this impl is only wired in when RUNTIME=azure.
"""
from __future__ import annotations

import jwt

from shared.config import Settings
from shared.interfaces.auth import AuthError, AuthProvider


class EntraAuthProvider(AuthProvider):
    def __init__(self, settings: Settings):
        self._s = settings
        # v2.0 metadata; works for Entra External ID (CIAM) tenants.
        self._jwks_uri = (
            f"https://login.microsoftonline.com/{settings.entra_tenant_id}/discovery/v2.0/keys"
        )
        self._jwks = jwt.PyJWKClient(self._jwks_uri)

    async def validate(self, bearer_token: str | None) -> str:
        if not bearer_token:
            raise AuthError("missing bearer token")
        token = bearer_token.removeprefix("Bearer ").strip()
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._s.entra_client_id,
                options={"require": ["exp", "iat"]},
            )
        except jwt.PyJWTError as e:
            raise AuthError(f"invalid token: {e}") from e
        user_id = payload.get(self._s.entra_user_id_claim) or payload.get("oid") or payload.get("sub")
        if not user_id:
            raise AuthError(f"token missing user id claim '{self._s.entra_user_id_claim}'")
        return user_id
