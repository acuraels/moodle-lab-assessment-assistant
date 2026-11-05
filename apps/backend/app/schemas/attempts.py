from datetime import datetime
from pydantic import BaseModel, Field


class AttemptResponse(BaseModel):
    id: str
    number: int
    submitted_at: datetime
    status: str
    ai_score: float | None = None
    ai_max_score: float | None = None
    ai_conclusion: str | None = None
    teacher_comment: str | None = None
    teacher_submitted: bool = False
    teacher_submitted_at: datetime | None = None


class CriterionResponse(BaseModel):
    name: str
    score: float
    max_score: float
    comment: str


class AIResultResponse(BaseModel):
    attempt_id: str
    status: str
    score: float | None = None
    max_score: float | None = None
    conclusion: str | None = None
    criteria: list[CriterionResponse] = Field(default_factory=list)
    settings_version: int | None = None
    checked_at: datetime | None = None
