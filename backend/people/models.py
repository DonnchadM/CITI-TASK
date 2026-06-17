"""Pydantic schemas for the people service.

``PersonCreate``/``PersonUpdate`` validate inbound payloads (types, required
fields, enums); the frontend mirrors these rules for UX but the backend remains
the source of truth. ``metadata`` is validated through :class:`PersonMetadata`,
which documents known fields yet allows extras — flexible but disciplined.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StaffType(str, Enum):
    """Whether a person is direct or non-direct staff."""

    DIRECT = "DIRECT"
    NON_DIRECT = "NON_DIRECT"


class PersonMetadata(BaseModel):
    """Free-form person metadata: documented known fields plus arbitrary extras."""

    model_config = ConfigDict(extra="allow")

    employee_id: Optional[str] = None
    department: Optional[str] = None


class PersonCreate(BaseModel):
    """Payload for creating a person (POST)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    staff_type: StaffType
    title: Optional[str] = Field(default=None, max_length=200)
    is_org_leader: bool = False
    metadata: PersonMetadata = Field(default_factory=PersonMetadata)


class PersonUpdate(BaseModel):
    """Payload for a full update of a person (PUT replaces all mutable fields)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    staff_type: StaffType
    title: Optional[str] = Field(default=None, max_length=200)
    is_org_leader: bool = False
    metadata: PersonMetadata = Field(default_factory=PersonMetadata)
