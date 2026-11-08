"""Only explicit teacher-authored numeric rubrics authorize numeric grading.

Free-form criteria are still useful as qualitative context. No model is allowed to
invent a grading scale or reinterpret a prose number as an official maximum.
"""
import json
from decimal import Decimal

from pydantic import Field, ValidationError, model_validator

from assessment_contract.schemas import EvaluationResult, RubricCriterion, StrictModel


class Rubric(StrictModel):
    criteria: list[RubricCriterion] = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def valid_scale(self):
        names = [row.name for row in self.criteria]
        if len(names) != len(set(names)):
            raise ValueError("Rubric names must be unique")
        if not 0 < sum(row.max_score for row in self.criteria) <= 1_000_000:
            raise ValueError("Rubric total must be positive and bounded")
        return self


def parse_rubric(text: str | None) -> list[RubricCriterion] | None:
    """Return a validated exact rubric, or None for qualitative-only assessment."""
    if not text:
        return None
    value = text.strip()
    if value.startswith("```json\n") and value.endswith("```"):
        value = value[8:-3].strip()
    try:
        payload = json.loads(value)
        return Rubric.model_validate(payload).criteria
    except (ValueError, TypeError, ValidationError):
        return None


def validate_result_for_rubric(
    result: EvaluationResult, rubric: list[RubricCriterion] | None
) -> EvaluationResult:
    if rubric is None:
        if result.criteria or result.score is not None or result.max_score is not None:
            raise ValueError("No explicit numeric rubric: only qualitative feedback is permitted")
        return result
    if len(result.criteria) != len(rubric):
        raise ValueError("Result must cover every teacher criterion exactly once")
    for actual, expected in zip(result.criteria, rubric, strict=True):
        if actual.name != expected.name or Decimal(str(actual.max_score)) != Decimal(str(expected.max_score)):
            raise ValueError("Result changed a teacher criterion or its maximum")
    return result
