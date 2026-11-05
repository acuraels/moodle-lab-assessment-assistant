from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import api_error
from app.middleware.session import UserContext, require_instructor
from app.models import Attempt, AttemptStatus, ReviewHistory, StoredFile
from app.routers.common import get_attempt, get_lab, now
from app.schemas.responses import ReviewInput

router = APIRouter(prefix="/api", tags=["instructor-attempts"])


@router.get("/instructor/attempts/{attempt_id}")
async def instructor_attempt(
    attempt_id: str,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    attempt = await get_attempt(db, attempt_id, user)
    if not attempt.teacher_submitted:
        raise api_error(404, "ATTEMPT_NOT_FOUND", "Attempt was not found")
    lab = await get_lab(db, attempt.lab_id, user)
    files = (
        await db.execute(select(StoredFile).where(StoredFile.attempt_id == attempt.id))
    ).scalars().all()
    return {
        "id": attempt.id,
        "lab": {
            "id": lab.id,
            "title": lab.title,
            "deadline": lab.deadline,
            "attempts_limit": lab.attempts_limit,
        },
        "student": {
            "id": attempt.student_id,
            "name": attempt.student_name,
            "Academic_group": attempt.academic_group,
        },
        "files": [
            {
                "id": file.id,
                "name": file.filename,
                "download_url": f"/api/files/{file.id}/download",
            }
            for file in files
        ],
        "submitted_at": attempt.submitted_at,
        "status": attempt.status,
        "ai_score": attempt.ai_score,
        "ai_max_score": attempt.ai_max_score,
        "ai_conclusion": attempt.ai_conclusion,
        "teacher_comment": attempt.teacher_comment,
        "actions": {
            "can_return_for_revision": attempt.status
            in {AttemptStatus.AI_CHECKED, AttemptStatus.RETURNED_FOR_REVISION},
            "can_accept": attempt.status
            in {AttemptStatus.AI_CHECKED, AttemptStatus.RETURNED_FOR_REVISION},
        },
    }


@router.post("/instructor/attempts/{attempt_id}/review")
async def review_attempt(
    attempt_id: str,
    payload: ReviewInput,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    attempt = await get_attempt(db, attempt_id, user)
    if not attempt.teacher_submitted:
        raise api_error(409, "ATTEMPT_NOT_SUBMITTED", "Attempt was not submitted to teacher")
    if attempt.status == AttemptStatus.ACCEPTED:
        raise api_error(409, "INVALID_ATTEMPT_STATUS", "Accepted attempt cannot be reviewed again")
    if payload.decision == "return_for_revision" and (
        payload.comment is None or not payload.comment.strip()
    ):
        raise api_error(400, "COMMENT_REQUIRED", "Comment is required for revision")
    reviewed_at = now()
    attempt.status = (
        AttemptStatus.ACCEPTED
        if payload.decision == "accept"
        else AttemptStatus.RETURNED_FOR_REVISION
    )
    attempt.teacher_comment = payload.comment
    attempt.reviewed_by = user.sub
    attempt.reviewed_at = reviewed_at
    db.add(
        ReviewHistory(
            id=str(uuid4()),
            attempt_id=attempt.id,
            decision=payload.decision,
            comment=payload.comment,
            reviewed_by=user.sub,
            reviewed_at=reviewed_at,
            ai_score=attempt.ai_score,
            ai_max_score=attempt.ai_max_score,
        )
    )
    await db.commit()
    return {
        "attempt_id": attempt.id,
        "status": attempt.status,
        "teacher_review": {
            "decision": payload.decision,
            "comment": payload.comment,
            "reviewed_by": user.sub,
            "reviewed_at": reviewed_at,
        },
    }


@router.post("/instructor/attempts/{attempt_id}/publish-grade")
async def publish_grade(
    attempt_id: str,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await get_attempt(db, attempt_id, user)
    raise api_error(
        501,
        "OUTCOMES_NOT_CONFIGURED",
        "Moodle Outcomes Service is not configured",
    )
