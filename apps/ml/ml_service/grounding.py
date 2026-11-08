"""Validate source quotations and adapt an internal assessment to the public API.

A matching quotation establishes where the text came from. It does not prove
that the model interpreted that text correctly; semantic quality needs separate
evaluation against reviewed examples.
"""
from decimal import Decimal
import re
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, ValidationError

from assessment_contract.schemas import (
    Criterion,
    EvaluationResult,
    RubricCriterion,
    Score,
    StrictModel,
)


Quotation = Annotated[str, StringConstraints(min_length=1, max_length=2000)]
Finding = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]


class GroundedCriterion(StrictModel):
    # Keep evidence and the finding before the grade in the generation schema.
    criterion_index: Annotated[int, Field(ge=0, le=49)]
    evidence: list[Quotation] = Field(min_length=1, max_length=3)
    comment: Finding
    verdict: Literal["met", "partial", "not_met"]
    score: Score


class GroundedAssessment(StrictModel):
    criteria: list[GroundedCriterion] = Field(min_length=1, max_length=50)


class GroundingError(ValueError):
    """A safe correction hint, never containing document or model prose."""

    def __init__(self, code: str, criterion_index: int | None = None):
        self.code = code
        self.criterion_index = criterion_index
        suffix = f":criterion_{criterion_index}" if criterion_index is not None else ""
        super().__init__(code + suffix)


def _normalized_source(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace while retaining positions in the original text."""
    chunks = []
    positions = []
    previous_end = 0
    for token in re.finditer(r"\S+", text):
        if chunks:
            chunks.append(" ")
            positions.append(previous_end)
        chunks.append(token.group())
        positions.extend(range(token.start(), token.end()))
        previous_end = token.end()
    return "".join(chunks), positions


def _quoted_source(
    quote: str,
    submission: str,
    normalized: str,
    positions: list[int],
    criterion_index: int,
) -> str:
    # No case folding, punctuation changes, Unicode compatibility folding, or
    # fuzzy matching: only runs of whitespace may differ from the source.
    needle = " ".join(quote.split())
    offset = normalized.find(needle) if needle else -1
    if offset < 0:
        raise GroundingError("evidence_not_found", criterion_index)
    start = positions[offset]
    end = positions[offset + len(needle) - 1] + 1
    first_line = submission.count("\n", 0, start) + 1
    last_line = submission.count("\n", 0, end) + 1
    line_range = str(first_line) if first_line == last_line else f"{first_line}–{last_line}"
    source_text = submission[start:end]
    # Whitespace in the original can be arbitrarily long. Retain the original
    # excerpt where bounded, otherwise show the equivalent bounded quotation.
    displayed_quote = source_text if len(source_text) <= 2000 else quote.strip()
    return f"Источник (строки извлечённого текста {line_range}): «{displayed_quote}»."


def _number(value: Decimal) -> str:
    result = format(value, "f")
    return result.rstrip("0").rstrip(".") if "." in result else result


def validate_and_adapt(
    assessment: GroundedAssessment | dict,
    rubric: list[RubricCriterion],
    submission: str,
) -> EvaluationResult:
    """Validate a complete ordered numeric assessment without inventing a scale."""
    if not rubric:
        raise GroundingError("rubric_required")
    try:
        draft = GroundedAssessment.model_validate(assessment)
    except ValidationError as exc:
        # Pydantic exceptions embed the invalid input, so never forward their
        # message to the correction prompt or logs.
        location = exc.errors(include_input=False)[0]["loc"]
        index = location[1] if len(location) > 1 and location[0] == "criteria" and isinstance(location[1], int) else None
        raise GroundingError("invalid_assessment", index) from None
    if len(draft.criteria) != len(rubric):
        raise GroundingError("criterion_count")

    normalized, positions = _normalized_source(submission)
    criteria = []
    counts = {"met": 0, "partial": 0, "not_met": 0}
    needs_work = []
    for index, (row, official) in enumerate(zip(draft.criteria, rubric, strict=True)):
        if row.criterion_index != index:
            raise GroundingError("criterion_order", index)
        score = Decimal(str(row.score))
        maximum = Decimal(str(official.max_score))
        if score < 0 or score > maximum:
            raise GroundingError("score_out_of_range", index)
        consistent = (
            row.verdict == "met" and score == maximum
            or row.verdict == "not_met" and score == 0
            or row.verdict == "partial" and 0 < score < maximum
        )
        if not consistent:
            raise GroundingError("verdict_score_mismatch", index)
        quotations = [
            _quoted_source(quote, submission, normalized, positions, index)
            for quote in row.evidence
        ]
        try:
            criteria.append(Criterion(
                name=official.name,
                max_score=official.max_score,
                score=row.score,
                comment=row.comment + "\n" + "\n".join(quotations),
            ))
        except ValidationError:
            raise GroundingError("invalid_criterion", index) from None
        counts[row.verdict] += 1
        if row.verdict != "met":
            needs_work.append(official.name)

    total = sum((Decimal(str(row.score)) for row in criteria), Decimal(0))
    maximum = sum((Decimal(str(row.max_score)) for row in criteria), Decimal(0))
    conclusion = (
        f"Предварительная оценка: {_number(total)} из {_number(maximum)}. "
        f"Проверено критериев: {len(criteria)}; выполнено полностью: {counts['met']}, "
        f"частично: {counts['partial']}, не выполнено: {counts['not_met']}."
    )
    if needs_work:
        conclusion += " Требуют доработки: " + "; ".join(needs_work) + "."
    conclusion += (
        " Проверка основана на извлечённом тексте; код не выполнялся, изображения "
        "не анализировались. Окончательное решение принимает преподаватель."
    )
    try:
        return EvaluationResult(
            score=float(total), max_score=float(maximum),
            conclusion=conclusion, criteria=criteria,
        )
    except ValidationError:
        raise GroundingError("invalid_result") from None
