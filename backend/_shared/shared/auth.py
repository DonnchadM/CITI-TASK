"""Authentication and authorization for all services (delivered via the layer).

Stateless JWT (HS256): a short-lived access token plus a longer refresh token.
Revocation is handled without a token store by comparing the token's ``ver`` claim
to the user's current ``token_version`` — bumping that value (logout, password or
role change) invalidates every outstanding token. Authorization is a single
declarative :data:`PERMISSIONS` map checked by :func:`require`, so the matrix is
defined once and enforced identically across every Lambda.
"""

import os
import time
from typing import Optional

import jwt

from .db import transaction
from .errors import Forbidden, Unauthenticated

JWT_SECRET = os.getenv("JWT_SECRET", "local-dev-jwt-secret-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TTL_SECONDS = int(os.getenv("ACCESS_TOKEN_TTL", str(15 * 60)))
REFRESH_TTL_SECONDS = int(os.getenv("REFRESH_TOKEN_TTL", str(7 * 24 * 60 * 60)))

ROLES = ("ADMIN", "MANAGER", "CONTRIBUTOR", "VIEWER")

# Role -> permitted actions. Mirrors the permission matrix in docs/DESIGN.md.
PERMISSIONS = {
    "ADMIN": {"read", "create", "update", "delete", "manage_users"},
    "MANAGER": {"read", "create", "update", "delete"},
    "CONTRIBUTOR": {"read", "create", "update"},
    "VIEWER": {"read"},
}


def _now() -> int:
    return int(time.time())


def create_access_token(user: dict) -> str:
    """Issue an access token carrying the user's role for stateless authorization."""
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "email": user["email"],
        "ver": user["token_version"],
        "type": "access",
        "iat": _now(),
        "exp": _now() + ACCESS_TTL_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def create_refresh_token(user: dict) -> str:
    """Issue a refresh token (no role claim; role is re-read on refresh)."""
    payload = {
        "sub": str(user["id"]),
        "ver": user["token_version"],
        "type": "refresh",
        "iat": _now(),
        "exp": _now() + REFRESH_TTL_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    """Decode and validate a token's signature, expiry, and type (raises 401)."""
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise Unauthenticated("Token has expired.")
    except jwt.InvalidTokenError:
        raise Unauthenticated("Invalid authentication token.")
    if claims.get("type") != expected_type:
        raise Unauthenticated("Invalid token type.")
    return claims


def _bearer_token(headers: dict) -> str:
    value = headers.get("authorization", "")
    if not value.lower().startswith("bearer "):
        raise Unauthenticated("A bearer access token is required.")
    return value.split(" ", 1)[1].strip()


def load_active_user(user_id: str) -> Optional[dict]:
    """Return the current row for an active user, or None."""
    with transaction() as cur:
        cur.execute(
            "SELECT id, email, role, is_active, token_version FROM app_user WHERE id = %s",
            [user_id],
        )
        return cur.fetchone()


def authenticate(request) -> dict:
    """Validate the request's access token against the live user (raises 401).

    Beyond signature/expiry, this checks the token's ``ver`` against the user's
    current ``token_version`` so revoked tokens are rejected even before expiry.
    """
    claims = decode_token(_bearer_token(request.headers), "access")
    user = load_active_user(claims["sub"])
    if user is None or not user["is_active"]:
        raise Unauthenticated("Account is inactive or no longer exists.")
    if user["token_version"] != claims.get("ver"):
        raise Unauthenticated("Token has been revoked; please log in again.")
    return claims


def require(claims: dict, action: str) -> None:
    """Authorize an action against the caller's role (raises 403)."""
    role = claims.get("role")
    if action not in PERMISSIONS.get(role, set()):
        raise Forbidden(f"Role '{role}' is not permitted to {action}.")
