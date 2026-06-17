"""auth service Lambda — login/refresh/logout, profile, and Admin user management.

Only login and refresh are public; every other route requires a valid access
token. Authorization for user management goes through the shared PERMISSIONS map
(manage_users), and the privilege-escalation safeguards from the design are
enforced here (no self role-change, no self-delete).
"""

import os

import repository as repo
from models import LoginRequest, PasswordChange, RefreshRequest, UserCreate, UserUpdate
from security import hash_password, verify_password

from shared.auth import (
    authenticate,
    create_access_token,
    create_refresh_token,
    decode_token,
    load_active_user,
    require,
)
from shared.db import ensure_schema
from shared.errors import Forbidden, NotFoundError, Unauthenticated, ValidationError
from shared.http import (
    Request,
    as_int,
    collection,
    json_response,
    lambda_app,
    no_content,
    resource_segments,
    validate,
)

_MAX_PAGE = 200
_DEFAULT_PAGE = 50
_seeded = False


def _ensure_seed() -> None:
    """Seed the bootstrap admin from env credentials, once per container."""
    global _seeded
    if _seeded:
        return
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")
    if email and password:
        repo.seed_admin(email, hash_password(password))
    _seeded = True


def _public(user: dict) -> dict:
    """Strip the password hash before returning a user to a client."""
    return {k: v for k, v in user.items() if k != "password_hash"}


def route(request: Request) -> dict:
    ensure_schema()
    _ensure_seed()
    segments = resource_segments(request, "auth")
    method = request.method

    if segments == ["login"] and method == "POST":
        return _login(request)
    if segments == ["refresh"] and method == "POST":
        return _refresh(request)
    if segments == ["logout"] and method == "POST":
        return _logout(request)
    if segments == ["me"] and method == "GET":
        return _me(request)
    if segments == ["me", "password"] and method == "PUT":
        return _change_password(request)

    if segments == ["users"]:
        if method == "GET":
            return _list_users(request)
        if method == "POST":
            return _create_user(request)
    elif len(segments) == 2 and segments[0] == "users":
        if method == "GET":
            return _get_user(request, segments[1])
        if method == "PUT":
            return _update_user(request, segments[1])
        if method == "DELETE":
            return _delete_user(request, segments[1])

    raise NotFoundError("No matching route for this request.")


# --- Public ------------------------------------------------------------------

def _login(request: Request) -> dict:
    data = validate(LoginRequest, request.body)
    user = repo.get_user_with_hash_by_email(data.email)
    if user is None or not user["is_active"] or not verify_password(
        data.password, user["password_hash"]
    ):
        raise Unauthenticated("Invalid email or password.")
    return json_response(
        200,
        {
            "access_token": create_access_token(user),
            "refresh_token": create_refresh_token(user),
            "user": _public(user),
        },
    )


def _refresh(request: Request) -> dict:
    data = validate(RefreshRequest, request.body)
    claims = decode_token(data.refresh_token, "refresh")
    user = load_active_user(claims["sub"])
    if user is None or not user["is_active"] or user["token_version"] != claims.get("ver"):
        raise Unauthenticated("Refresh token is invalid or has been revoked.")
    return json_response(200, {"access_token": create_access_token(user)})


# --- Authenticated self-service ----------------------------------------------

def _logout(request: Request) -> dict:
    claims = authenticate(request)
    repo.bump_token_version(claims["sub"])
    return no_content()


def _me(request: Request) -> dict:
    claims = authenticate(request)
    return json_response(200, _public(repo.get_user(claims["sub"])))


def _change_password(request: Request) -> dict:
    claims = authenticate(request)
    data = validate(PasswordChange, request.body)
    user = repo.get_user_with_hash(claims["sub"])
    if not verify_password(data.current_password, user["password_hash"]):
        raise ValidationError("The current password is incorrect.")
    repo.set_password(claims["sub"], hash_password(data.new_password))
    return no_content()


# --- Admin user management (manage_users) ------------------------------------

def _list_users(request: Request) -> dict:
    claims = authenticate(request)
    require(claims, "manage_users")
    limit = as_int(request.query.get("limit"), _DEFAULT_PAGE, _MAX_PAGE)
    offset = as_int(request.query.get("offset"), 0)
    rows, total = repo.list_users(limit, offset)
    return collection([_public(u) for u in rows], limit, offset, total)


def _create_user(request: Request) -> dict:
    claims = authenticate(request)
    require(claims, "manage_users")
    data = validate(UserCreate, request.body)
    user = repo.create_user(
        data.email, hash_password(data.password), data.role.value, data.is_active, data.person_id
    )
    return json_response(201, _public(user))


def _get_user(request: Request, user_id: str) -> dict:
    claims = authenticate(request)
    require(claims, "manage_users")
    return json_response(200, _public(repo.get_user(user_id)))


def _update_user(request: Request, user_id: str) -> dict:
    claims = authenticate(request)
    require(claims, "manage_users")
    data = validate(UserUpdate, request.body)
    if user_id == claims["sub"] and data.role.value != claims["role"]:
        raise Forbidden("You cannot change your own role.")
    return json_response(
        200, _public(repo.update_user(user_id, data.role.value, data.is_active, data.person_id))
    )


def _delete_user(request: Request, user_id: str) -> dict:
    claims = authenticate(request)
    require(claims, "manage_users")
    if user_id == claims["sub"]:
        raise Forbidden("You cannot delete your own account.")
    repo.delete_user(user_id)
    return no_content()


handler = lambda_app(route)
