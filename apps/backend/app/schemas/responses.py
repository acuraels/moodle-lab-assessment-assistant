from typing import Literal

from pydantic import BaseModel, Field


class ReviewInput(BaseModel):
    decision: Literal["accept", "return_for_revision"]
    comment: str | None = Field(default=None, max_length=10000)
