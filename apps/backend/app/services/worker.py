"""Sequential processing using persisted attempts, without a separate queue.

Run one Uvicorn process. A short lease protects against duplicate calls and
expires after a crash so another process run can resume the job.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from pathlib import PurePath
from time import monotonic

from pydantic import ValidationError
from sqlalchemy import or_, select, update

from assessment_contract.schemas import EvaluationRequest

from app.config import settings
from app.database import SessionLocal
from app.models import Attempt, AttemptStatus, FilePurpose, StoredFile
from app.services.ai_snapshot import MATERIAL_FIELDS
from app.services.ml_client import EvaluationInput, MLFailure, evaluate


logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def as_utc(value: datetime) -> datetime:
    # SQLite fixtures use naive timestamps; PostgreSQL uses timestamptz.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def due(at: datetime):
    return or_(Attempt.ai_next_retry_at.is_(None), Attempt.ai_next_retry_at <= at)


async def _prepare(db, attempt: Attempt) -> EvaluationInput:
    snapshot = attempt.ai_input_snapshot
    if (not isinstance(snapshot, dict) or snapshot.get("lab_id") != attempt.lab_id
            or snapshot.get("settings_version") != attempt.settings_version
            or not isinstance(snapshot.get("materials"), dict)):
        raise MLFailure("INVALID_SNAPSHOT")
    submissions = (await db.scalars(select(StoredFile).where(
        StoredFile.attempt_id == attempt.id, StoredFile.lab_id == attempt.lab_id,
        StoredFile.purpose == FilePurpose.ATTEMPT,
    ))).all()
    if len(submissions) != 1:
        raise MLFailure("SUBMISSION_NOT_FOUND")

    def attachment(key: str, stored: StoredFile):
        if len(stored.data) > settings.max_file_size_bytes:
            raise MLFailure("FILE_TOO_LARGE")
        # Do not transmit a student's name through the original filename.
        suffix = PurePath(stored.filename).suffix.lower()
        return (key, (f"{key}{suffix}", stored.data, stored.content_type))

    files = [attachment("submission", submissions[0])]
    materials = {}
    for field, material in snapshot["materials"].items():
        if field not in MATERIAL_FIELDS or not isinstance(material, dict):
            raise MLFailure("INVALID_SNAPSHOT")
        if set(material) == {"text"}:
            materials[field] = {"text": material["text"]}
        elif set(material) == {"file_id"} and isinstance(material["file_id"], str):
            stored = await db.scalar(select(StoredFile).where(
                StoredFile.id == material["file_id"], StoredFile.lab_id == attempt.lab_id,
                StoredFile.purpose == FilePurpose.AI_SETTING,
                StoredFile.attempt_id.is_(None),
            ))
            if stored is None:
                raise MLFailure("MATERIAL_NOT_FOUND")
            materials[field] = {"file_key": field}
            files.append(attachment(field, stored))
        else:
            raise MLFailure("INVALID_SNAPSHOT")
    try:
        metadata = EvaluationRequest(
            attempt_id=attempt.id, lab_id=attempt.lab_id,
            title=snapshot.get("title"), description=snapshot.get("description"),
            settings_version=attempt.settings_version, materials=materials,
        )
    except ValidationError as exc:
        raise MLFailure("INVALID_SNAPSHOT") from exc
    return EvaluationInput(metadata=metadata, files=files)


async def _finish_failure(attempt_id: str, claim: int, failure: MLFailure, deadline: datetime) -> None:
    now = utcnow()
    retry_at = now + timedelta(seconds=settings.ml_retry_delay_seconds)
    retry = failure.retryable and claim < settings.ml_max_attempts and retry_at < deadline
    values = {
        "ai_next_retry_at": retry_at if retry else None,
        "ai_error_code": None if retry else failure.code,
        "ai_error_message": None if retry else failure.message,
    }
    if not retry:
        values.update(status=AttemptStatus.AI_FAILED, ai_score=None, ai_max_score=None,
                      ai_conclusion=None, ai_criteria=None, ai_checked_at=None)
    async with SessionLocal() as db:
        await db.execute(update(Attempt).where(
            Attempt.id == attempt_id, Attempt.status == AttemptStatus.PROCESSING,
            Attempt.ai_processing_attempts == claim,
        ).values(**values))
        await db.commit()
    logger.warning("ML attempt=%s code=%s call=%d retry=%s", attempt_id, failure.code, claim, retry)


async def process_attempt(attempt_id: str) -> None:
    started = monotonic()
    failure = None
    now = utcnow()
    async with SessionLocal() as db:
        attempt = await db.get(Attempt, attempt_id)
        if attempt is None or attempt.status != AttemptStatus.PROCESSING:
            return
        # An old pre-ML job cannot use today's materials as its original input.
        deadline = as_utc(attempt.ai_deadline_at) if attempt.ai_deadline_at else now
        expired = deadline <= now
        if not expired and attempt.ai_next_retry_at and as_utc(attempt.ai_next_retry_at) > now:
            return
        previous = attempt.ai_processing_attempts
        claim = previous + 1
        remaining = max(0.01, (deadline - now).total_seconds())
        timeout = min(settings.ml_timeout_seconds, remaining)
        claimed = await db.execute(update(Attempt).where(
            Attempt.id == attempt.id, Attempt.status == AttemptStatus.PROCESSING,
            Attempt.ai_processing_attempts == previous,
            or_(due(now), Attempt.ai_deadline_at <= now, Attempt.ai_deadline_at.is_(None)),
        ).execution_options(synchronize_session=False).values(ai_processing_attempts=claim,
                 ai_next_retry_at=now + timedelta(seconds=timeout + 5)))
        if claimed.rowcount != 1:
            await db.rollback()
            return
        await db.commit()
        if not attempt.ai_input_snapshot:
            failure = MLFailure("INVALID_SNAPSHOT")
        elif expired:
            failure = MLFailure("PROCESSING_EXPIRED")
        elif previous >= settings.ml_max_attempts:
            failure = MLFailure("RETRY_LIMIT_EXCEEDED")
        else:
            try:
                payload = await _prepare(db, attempt)
            except MLFailure as exc:
                failure = exc
        # Close DB connection before any inference/network wait.

    if failure is not None:
        await _finish_failure(attempt_id, claim, failure, deadline)
        return
    try:
        result = await evaluate(payload, timeout)
        if utcnow() >= deadline:
            raise MLFailure("PROCESSING_EXPIRED")
    except MLFailure as exc:
        await _finish_failure(attempt_id, claim, exc, deadline)
        return
    except Exception as exc:
        # Do not log document contents, prompts or remote response details.
        logger.error("ML attempt=%s unexpected_exception=%s", attempt_id, type(exc).__name__)
        await _finish_failure(attempt_id, claim, MLFailure("ML_INTERNAL_ERROR"), deadline)
        return

    async with SessionLocal() as db:
        saved = await db.execute(update(Attempt).where(
            Attempt.id == attempt_id, Attempt.status == AttemptStatus.PROCESSING,
            Attempt.ai_processing_attempts == claim,
        ).values(
            status=AttemptStatus.AI_CHECKED, ai_score=result.score, ai_max_score=result.max_score,
            ai_conclusion=result.conclusion,
            ai_criteria=[criterion.model_dump() for criterion in result.criteria],
            ai_checked_at=utcnow(), ai_error_code=None, ai_error_message=None, ai_next_retry_at=None,
        ))
        await db.commit()
    logger.info("ML attempt=%s saved=%s elapsed_seconds=%.2f", attempt_id, saved.rowcount == 1, monotonic() - started)


async def consume_attempts() -> None:
    while True:
        try:
            async with SessionLocal() as db:
                now = utcnow()
                attempt_id = await db.scalar(select(Attempt.id).where(
                    Attempt.status == AttemptStatus.PROCESSING,
                    or_(due(now), Attempt.ai_deadline_at <= now, Attempt.ai_deadline_at.is_(None)),
                ).order_by(Attempt.submitted_at, Attempt.id).limit(1))
            if attempt_id is None:
                await asyncio.sleep(settings.ml_poll_seconds)
            else:
                await process_attempt(attempt_id)
        except asyncio.CancelledError:
            # Lease + persisted call count permit bounded recovery on restart.
            raise
        except Exception as exc:
            logger.error("ML consumer exception=%s", type(exc).__name__)
            await asyncio.sleep(settings.ml_poll_seconds)
