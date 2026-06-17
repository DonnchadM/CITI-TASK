"""Pydantic schemas for the auth service.

Email is validated with a simple pattern rather than Pydantic's EmailStr to avoid
pulling in the email-validator dependency; the backend remains the source of truth.
"""

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

_EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class Role(str, Enum):
    """RBAC roles, highest to lowest privilege."""

    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    CONTRIBUTOR = "CONTRIBUTOR"
    VIEWER = "VIEWER"


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(min_length=1)


class PasswordChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8, max_length=200)


class UserCreate(BaseModel):
    """Admin-created user account."""

    model_config = ConfigDict(extra="forbid")

    email: str = Field(pattern=_EMAIL_PATTERN)
    password: str = Field(min_length=8, max_length=200)
    role: Role
    is_active: bool = True
    person_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    """Admin full-update of a user's role/status (password has its own flow)."""

    model_config = ConfigDict(extra="forbid")

    role: Role
    is_active: bool = True
    person_id: Optional[uuid.UUID] = None
