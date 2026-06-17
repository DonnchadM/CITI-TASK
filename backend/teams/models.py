"""Pydantic schemas for the teams service.

UUID foreign keys (leader, reports-to, member person) are typed as UUID so
malformed ids are rejected as 400s by validation; the repository then checks the
referenced rows actually exist.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TeamMetadata(BaseModel):
    """Free-form team metadata: documented known fields plus arbitrary extras."""

    model_config = ConfigDict(extra="allow")

    cost_center: Optional[str] = None


class TeamCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    leader_id: Optional[uuid.UUID] = None
    reports_to_id: Optional[uuid.UUID] = None
    metadata: TeamMetadata = Field(default_factory=TeamMetadata)


class TeamUpdate(BaseModel):
    """Full update of a team (PUT replaces all mutable fields)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    location: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = None
    leader_id: Optional[uuid.UUID] = None
    reports_to_id: Optional[uuid.UUID] = None
    metadata: TeamMetadata = Field(default_factory=TeamMetadata)


class MemberAdd(BaseModel):
    """Add a person to a team."""

    model_config = ConfigDict(extra="forbid")

    person_id: uuid.UUID
    role_in_team: Optional[str] = Field(default=None, max_length=200)


class MemberUpdate(BaseModel):
    """Update a person's role within a team."""

    model_config = ConfigDict(extra="forbid")

    role_in_team: Optional[str] = Field(default=None, max_length=200)
