from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.errors import api_error
from app.middleware.session import UserContext, require_instructor
from app.models import Attempt, AttemptStatus
from app.routers.common import get_lab, now, pages

router = APIRouter(prefix="/api", tags=["submissions"])


@router.get("/labs/{lab_id}/submissions")
async def list_submissions(
    lab_id: str,
    status: str = Query("all"),
    student_name: str | None = Query(None),
    Academic_group: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await get_lab(db, lab_id, user)
    if status not in {"all", AttemptStatus.AI_CHECKED, AttemptStatus.RETURNED_FOR_REVISION}:
        raise api_error(400, "INVALID_STATUS", "Unsupported submissions status")
    filters = [Attempt.lab_id == lab_id, Attempt.teacher_submitted.is_(True)]
    if status != "all":
        filters.append(Attempt.status == status)
    if student_name:
        filters.append(Attempt.student_name.ilike(f"%{student_name}%"))
    if Academic_group:
        group_exists = await db.scalar(
            select(Attempt.id)
            .where(
                Attempt.lab_id == lab_id,
                Attempt.teacher_submitted.is_(True),
                Attempt.academic_group == Academic_group,
            )
            .limit(1)
        )
        if group_exists is None:
            raise api_error(400, "INVALID_GROUP", "Academic group is not available")
        filters.append(Attempt.academic_group == Academic_group)
    query = select(Attempt).options(selectinload(Attempt.files)).where(*filters)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = (
        await db.execute(
            query.order_by(Attempt.submitted_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return {
        "items": [
            {
                "attempt_id": row.id,
                "student": {
                    "id": row.student_id,
                    "name": row.student_name,
                    "Academic_group": row.academic_group,
                },
                "submitted_at": row.submitted_at,
                "ai_score": row.ai_score,
                "ai_max_score": row.ai_max_score,
                "file_count": len(row.files),
                "status": row.status,
            }
            for row in rows
        ],
        "pagination": pages(page, page_size, total),
    }


@router.get("/labs/{lab_id}/submissions/statistics")
async def submissions_statistics(
    lab_id: str,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await get_lab(db, lab_id, user)
    today = now().date()
    submitted_filter = [Attempt.lab_id == lab_id, Attempt.teacher_submitted.is_(True)]
    total_submitted = await db.scalar(select(func.count()).where(*submitted_filter)) or 0
    submitted_today = await db.scalar(
        select(func.count()).where(
            *submitted_filter,
            func.date(Attempt.teacher_submitted_at) == today,
        )
    ) or 0
    counts = {}
    for state in (
        AttemptStatus.AI_CHECKED,
        AttemptStatus.ACCEPTED,
        AttemptStatus.RETURNED_FOR_REVISION,
        AttemptStatus.PROCESSING,
    ):
        state_filter = [Attempt.lab_id == lab_id, Attempt.status == state]
        if state != AttemptStatus.PROCESSING:
            state_filter.append(Attempt.teacher_submitted.is_(True))
        counts[state] = await db.scalar(select(func.count()).where(*state_filter)) or 0
    return {
        "lab_id": lab_id,
        "statistics": {
            "total_submitted": total_submitted,
            "submitted_today": submitted_today,
            "ai_checked": counts[AttemptStatus.AI_CHECKED],
            "accepted": counts[AttemptStatus.ACCEPTED],
            "returned_for_revision": counts[AttemptStatus.RETURNED_FOR_REVISION],
            "processing": counts[AttemptStatus.PROCESSING],
        },
        "calculated_at": now(),
    }


@router.get("/labs/{lab_id}/submission-groups")
async def submission_groups(
    lab_id: str,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    await get_lab(db, lab_id, user)
    rows = await db.execute(
        select(Attempt.academic_group)
        .where(
            Attempt.lab_id == lab_id,
            Attempt.teacher_submitted.is_(True),
            Attempt.academic_group.is_not(None),
        )
        .distinct()
        .order_by(Attempt.academic_group)
    )
    return {"items": [{"Academic_group": group} for (group,) in rows.all()]}
