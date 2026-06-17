"""Pydantic schema for the assistant service."""

from pydantic import BaseModel, ConfigDict, Field


class AssistantQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
