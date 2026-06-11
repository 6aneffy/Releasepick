"""Pydantic models for card news plan (LLM output + UI state)."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class SlideRole(str, Enum):
    cover = "cover"
    body = "body"
    closing = "closing"


class SlidePlan(BaseModel):
    role: SlideRole
    title: str = Field(..., max_length=500)
    bullets: list[str] = Field(default_factory=list)
    footnote: str | None = Field(default=None, max_length=300)

    @field_validator("bullets", mode="before")
    @classmethod
    def _bullets(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return []


class CardNewsPlan(BaseModel):
    series_title: str = Field(..., max_length=200)
    head_copy: str = Field(..., max_length=300)
    slides: list[SlidePlan] = Field(default_factory=list)

    @field_validator("slides", mode="before")
    @classmethod
    def _slides(cls, v: Any) -> list[Any]:
        if v is None:
            return []
        return v

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_json_dict(cls, data: dict[str, Any]) -> CardNewsPlan:
        return cls.model_validate(data)
