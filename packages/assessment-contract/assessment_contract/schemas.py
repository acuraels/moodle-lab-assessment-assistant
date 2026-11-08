from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

MaterialName = Literal[
    "methodical_guide", "grading_criteria", "system_instructions", "reference_work"
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Score = Annotated[float, Field(strict=True, ge=0, le=1_000_000, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class MaterialInput(StrictModel):
    text: Annotated[str, Field(min_length=1, max_length=500_000)] | None = None
    file_key: MaterialName | None = None

    @model_validator(mode="after")
    def one_source(self) -> Self:
        if (self.text is None) == (self.file_key is None):
            raise ValueError("Material must contain exactly one of text or file_key")
        if self.text is not None and not self.text.strip():
            raise ValueError("Material text must not be blank")
        return self


class EvaluationRequest(StrictModel):
    attempt_id: Annotated[str, Field(min_length=1, max_length=128)]
    lab_id: Annotated[str, Field(min_length=1, max_length=128)]
    title: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=500_000)] | None = None
    settings_version: Annotated[int, Field(ge=1)]
    materials: dict[MaterialName, MaterialInput] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def matching_keys(self) -> Self:
        for category, material in self.materials.items():
            if material.file_key is not None and material.file_key != category:
                raise ValueError("Material file_key must match its category")
        return self


class RubricCriterion(StrictModel):
    name: Name
    max_score: Score


class Criterion(RubricCriterion):
    score: Score
    comment: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=10_000)]

    @model_validator(mode="after")
    def bounded_score(self) -> Self:
        if self.score > self.max_score:
            raise ValueError("Criterion score exceeds its maximum")
        return self


class EvaluationResult(StrictModel):
    score: Score | None
    max_score: Score | None
    conclusion: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30_000)]
    criteria: list[Criterion] = Field(max_length=50)

    @model_validator(mode="after")
    def consistent_scores(self) -> Self:
        if not self.criteria:
            if self.score is not None or self.max_score is not None:
                raise ValueError("An unscored assessment must have null totals and no numeric criteria")
            return self
        if self.score is None or self.max_score is None or self.max_score <= 0:
            raise ValueError("Numeric criteria require totals and a positive overall maximum")
        names = [criterion.name for criterion in self.criteria]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate criterion names")
        if self.score > self.max_score:
            raise ValueError("Total score exceeds maximum")
        for field in ("score", "max_score"):
            expected = sum((Decimal(str(getattr(row, field))) for row in self.criteria), Decimal(0))
            if abs(Decimal(str(getattr(self, field))) - expected) > Decimal("0.000001"):
                raise ValueError(f"{field} must equal the sum of criterion values")
        return self


class EvaluationError(StrictModel):
    code: Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]{0,63}$")]
    message: Annotated[str, Field(min_length=1, max_length=1000)]
    retryable: bool = False
