from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AttemptResponse(BaseModel):
    id: str
    number: int
    submitted_at: datetime
    status: str
    ai_score: float | None = None
    ai_conclusion: str | None = None
    teacher_comment: str | None = None


class AIResultResponse(BaseModel):
    attempt_id: str
    status: str
    score: float | None = None
    max_score: float | None = None
    conclusion: str | None = None
    criteria: list[dict[str, Any]] = Field(default_factory=list)
    settings_version: int | None = None
    checked_at: datetime | None = None
