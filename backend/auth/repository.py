"""SQL data access for auth users.

Password hashes are never returned in the public column set; only the explicit
``*_with_hash`` lookups include them, for credential verification.
"""

from typing import List, Optional, Tuple

import psycopg

from shared.db import transaction
from shared.errors import ConflictError, NotFoundError
from shared.http import path_uuid

# Columns safe to return to clients (never the password hash).
_PUBLIC = "id, email, role, is_active, token_version, person_id, created_at, updated_at"


def get_user_with_hash_by_email(email: str) -> Optional[dict]:
    """Return a user including password_hash (for login), or None."""
    with transaction() as cur:
        cur.execute(
            f"SELECT {_PUBLIC}, password_hash FROM app_user WHERE email = %s", [email]  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        )
        return cur.fetchone()


def get_user_with_hash(user_id: str) -> dict:
    with transaction() as cur:
        cur.execute(
            f"SELECT {_PUBLIC}, password_hash FROM app_user WHERE id = %s",  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            [path_uuid(user_id)],
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("User not found.")
    return row


def get_user(user_id: str) -> dict:
    with transaction() as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM app_user WHERE id = %s", [path_uuid(user_id)])  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("User not found.")
    return row


def list_users(limit: int, offset: int) -> Tuple[List[dict], int]:
    with transaction() as cur:
        cur.execute("SELECT COUNT(*) AS total FROM app_user")
        total = cur.fetchone()["total"]
        cur.execute(
            f"SELECT {_PUBLIC} FROM app_user ORDER BY created_at DESC, id LIMIT %s OFFSET %s",  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            [limit, offset],
        )
        return cur.fetchall(), total


def create_user(
    email: str, password_hash: str, role: str, is_active: bool, person_id: Optional[str]
) -> dict:
    try:
        with transaction() as cur:
            cur.execute(
                f"INSERT INTO app_user (email, password_hash, role, is_active, person_id) "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
                f"VALUES (%s, %s, %s, %s, %s) RETURNING {_PUBLIC}",
                [email, password_hash, role, is_active, person_id],
            )
            return cur.fetchone()
    except psycopg.errors.UniqueViolation:
        raise ConflictError("A user with that email already exists.")


def update_user(
    user_id: str, role: str, is_active: bool, person_id: Optional[str]
) -> dict:
    """Full-update a user; bump token_version when the role changes (revocation)."""
    with transaction() as cur:
        cur.execute(
            "UPDATE app_user SET role = %s, is_active = %s, person_id = %s, "  # nosec B608 - parameterized query; only code-controlled identifiers are interpolated
            "token_version = token_version + (role <> %s)::int, updated_at = now() "
            f"WHERE id = %s RETURNING {_PUBLIC}",
            [role, is_active, person_id, role, path_uuid(user_id)],
        )
        row = cur.fetchone()
    if row is None:
        raise NotFoundError("User not found.")
    return row


def set_password(user_id: str, password_hash: str) -> None:
    """Update a password and bump token_version to log out existing sessions."""
    with transaction() as cur:
        cur.execute(
            "UPDATE app_user SET password_hash = %s, token_version = token_version + 1, "
            "updated_at = now() WHERE id = %s",
            [password_hash, path_uuid(user_id)],
        )
        if cur.rowcount == 0:
            raise NotFoundError("User not found.")


def bump_token_version(user_id: str) -> None:
    """Invalidate all of a user's tokens (logout)."""
    with transaction() as cur:
        cur.execute(
            "UPDATE app_user SET token_version = token_version + 1, updated_at = now() "
            "WHERE id = %s",
            [path_uuid(user_id)],
        )
        if cur.rowcount == 0:
            raise NotFoundError("User not found.")


def delete_user(user_id: str) -> None:
    with transaction() as cur:
        cur.execute("DELETE FROM app_user WHERE id = %s", [path_uuid(user_id)])
        if cur.rowcount == 0:
            raise NotFoundError("User not found.")


def seed_admin(email: str, password_hash: str) -> None:
    """Create the bootstrap admin if no admin exists yet (idempotent)."""
    with transaction() as cur:
        cur.execute("SELECT 1 FROM app_user WHERE role = 'ADMIN' LIMIT 1")
        if cur.fetchone() is not None:
            return
        cur.execute(
            "INSERT INTO app_user (email, password_hash, role) VALUES (%s, %s, 'ADMIN') "
            "ON CONFLICT (email) DO NOTHING",
            [email, password_hash],
        )
