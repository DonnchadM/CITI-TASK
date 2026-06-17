"""Pydantic schemas for the achievements service.

``month`` is normalized to the first of the month so monthly achievements group
and filter consistently regardless of the day supplied.
"""

import uuid
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AchievementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: uuid.UUID
    month: date
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None

    @field_validator("month")
    @classmethod
    def normalize_month(cls, value: date) -> date:
        return value.replace(day=1)


class AchievementUpdate(BaseModel):
    """Full update of an achievement (PUT replaces all mutable fields)."""

    model_config = ConfigDict(extra="forbid")

    team_id: uuid.UUID
    month: date
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None

    @field_validator("month")
    @classmethod
    def normalize_month(cls, value: date) -> date:
        return value.replace(day=1)
