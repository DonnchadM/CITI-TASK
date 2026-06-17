"""Unit tests: JWT issuing/decoding and the RBAC permission matrix."""

import pytest

from shared.auth import (
    PERMISSIONS, create_access_token, create_refresh_token, decode_token, require,
)
from shared.errors import Forbidden, Unauthenticated

USER = {
    "id": "5c138c12-bae5-4d49-b0a9-784d3053cd41",
    "email": "admin@example.com",
    "role": "ADMIN",
    "token_version": 0,
}


def test_access_token_roundtrip():
    claims = decode_token(create_access_token(USER), "access")
    assert claims["sub"] == USER["id"]
    assert claims["role"] == "ADMIN"
    assert claims["email"] == "admin@example.com"
    assert claims["ver"] == 0
    assert claims["type"] == "access"


def test_refresh_token_type():
    assert decode_token(create_refresh_token(USER), "refresh")["type"] == "refresh"


def test_decode_wrong_type_rejected():
    access = create_access_token(USER)
    with pytest.raises(Unauthenticated):
        decode_token(access, "refresh")


def test_decode_garbage_rejected():
    with pytest.raises(Unauthenticated):
        decode_token("not.a.jwt", "access")


def test_permission_matrix():
    assert PERMISSIONS["ADMIN"] == {"read", "create", "update", "delete", "manage_users"}
    assert PERMISSIONS["VIEWER"] == {"read"}
    # contributor can create/update but not delete or manage users
    assert "create" in PERMISSIONS["CONTRIBUTOR"]
    assert "delete" not in PERMISSIONS["CONTRIBUTOR"]


def test_require_allows_and_denies():
    require({"role": "VIEWER"}, "read")           # allowed, no raise
    require({"role": "MANAGER"}, "delete")        # allowed, no raise
    with pytest.raises(Forbidden):
        require({"role": "VIEWER"}, "create")
    with pytest.raises(Forbidden):
        require({"role": "MANAGER"}, "manage_users")
