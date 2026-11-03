from pathlib import PurePath
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Query, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.errors import api_error
from app.middleware.session import UserContext, get_current_user, require_student
from app.models import AISettings, Attempt, AttemptStatus, FilePurpose, StoredFile
from app.routers.common import attempt_item, get_attempt, get_lab, now, pages
from app.schemas.attempts import AIResultResponse
from app.services.files import ALLOWED_ATTEMPT_TYPES, read_upload
from app.services.worker import process_attempt

router = APIRouter(prefix="/api", tags=["student-attempts"])


@router.get("/labs/{lab_id}/attempts")
async def list_attempts(
    lab_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: UserContext = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    await get_lab(db, lab_id, user)
    base = (
        select(Attempt)
        .options(selectinload(Attempt.files))
        .where(Attempt.lab_id == lab_id, Attempt.student_id == user.sub)
    )
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (
        await db.execute(
            base.order_by(Attempt.submitted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {"items": [attempt_item(row) for row in rows], "pagination": pages(page, page_size, total)}


@router.post("/labs/{lab_id}/attempts", status_code=202)
async def create_attempt(
    lab_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: UserContext = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    lab = await get_lab(db, lab_id, user)
    if await db.get(AISettings, lab.id) is None:
        raise api_error(409, "AI_SETTINGS_NOT_CONFIGURED", "AI settings are not configured")
    count = await db.scalar(
        select(func.count()).where(Attempt.lab_id == lab.id, Attempt.student_id == user.sub)
    ) or 0
    if lab.attempts_limit is not None and count >= lab.attempts_limit:
        raise api_error(409, "ATTEMPT_LIMIT_REACHED", "Attempt limit reached")
    try:
        data = await read_upload(file, ALLOWED_ATTEMPT_TYPES)
    except ValueError as exc:
        code = str(exc)
        raise api_error(413 if code == "FILE_TOO_LARGE" else 415, code, code)
    attempt = Attempt(
        id=str(uuid4()),
        lab_id=lab.id,
        student_id=user.sub,
        student_name=user.name,
        academic_group=user.Academic_group,
        number=count + 1,
        submitted_at=now(),
        teacher_submitted=False,
        status=AttemptStatus.PROCESSING,
    )
    db.add(attempt)
    db.add(
        StoredFile(
            id=str(uuid4()),
            lab_id=lab.id,
            attempt_id=attempt.id,
            purpose=FilePurpose.ATTEMPT,
            filename=PurePath(file.filename or "submission").name,
            content_type=file.content_type or "application/octet-stream",
            size=len(data),
            data=data,
            created_at=now(),
        )
    )
    await db.commit()
    await db.refresh(attempt, attribute_names=["files"])
    background_tasks.add_task(process_attempt, attempt.id)
    return attempt_item(attempt)


@router.get("/attempts/{attempt_id}")
async def read_attempt(
    attempt_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "student":
        raise api_error(403, "STUDENT_ROLE_REQUIRED", "Student role required")
    return attempt_item(await get_attempt(db, attempt_id, user))


@router.post("/attempts/{attempt_id}/submit-to-teacher")
async def submit_to_teacher(
    attempt_id: str,
    user: UserContext = Depends(require_student),
    db: AsyncSession = Depends(get_db),
):
    attempt = await get_attempt(db, attempt_id, user)
    if attempt.status not in {AttemptStatus.AI_CHECKED, AttemptStatus.RETURNED_FOR_REVISION}:
        raise api_error(409, "INVALID_ATTEMPT_STATUS", "Attempt is not ready to submit")
    attempt.teacher_submitted = True
    attempt.teacher_submitted_at = attempt.teacher_submitted_at or now()
    await db.commit()
    return {"id": attempt.id, "status": attempt.status}


@router.get("/attempts/{attempt_id}/ai-result", response_model=AIResultResponse)
async def ai_result(
    attempt_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    attempt = await get_attempt(db, attempt_id, user)
    payload = AIResultResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        score=attempt.ai_score,
        max_score=attempt.ai_max_score,
        conclusion=attempt.ai_conclusion,
        criteria=attempt.ai_criteria or [],
        settings_version=attempt.settings_version,
        checked_at=attempt.ai_checked_at,
    )
    if attempt.status == AttemptStatus.PROCESSING:
        return JSONResponse(status_code=202, content=payload.model_dump(mode="json"))
    return payload
