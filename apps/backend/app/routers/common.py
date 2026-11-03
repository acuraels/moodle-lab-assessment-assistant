from datetime import datetime, timezone
from math import ceil

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import api_error
from app.middleware.session import UserContext
from app.models import Attempt, Lab


def now() -> datetime:
    return datetime.now(timezone.utc)


def pages(page: int, page_size: int, total: int) -> dict[str, int]:
    return {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": ceil(total / page_size) if total else 0,
    }


async def get_lab(db: AsyncSession, lab_id: str, user: UserContext) -> Lab:
    lab = await db.get(Lab, lab_id)
    if lab is None or lab.course_id != user.course_id:
        raise api_error(404, "LAB_NOT_FOUND", "Laboratory was not found")
    if user.role == "student" and lab.id != user.lab_id:
        raise api_error(404, "LAB_NOT_FOUND", "Laboratory was not found")
    return lab


def attempt_item(attempt: Attempt) -> dict:
    return {
        "id": attempt.id,
        "number": attempt.number,
        "submitted_at": attempt.submitted_at,
        "status": attempt.status,
        "ai_score": attempt.ai_score,
        "ai_conclusion": attempt.ai_conclusion,
        "teacher_comment": attempt.teacher_comment,
        "file": (
            {
                "id": attempt.files[0].id,
                "name": attempt.files[0].filename,
                "size": attempt.files[0].size,
            }
            if attempt.files
            else None
        ),
    }


async def get_attempt(db: AsyncSession, attempt_id: str, user: UserContext) -> Attempt:
    attempt = (
        await db.execute(
            select(Attempt)
            .options(selectinload(Attempt.files))
            .where(Attempt.id == attempt_id)
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise api_error(404, "ATTEMPT_NOT_FOUND", "Attempt was not found")
    lab = await db.get(Lab, attempt.lab_id)
    if lab is None or lab.course_id != user.course_id:
        raise api_error(404, "ATTEMPT_NOT_FOUND", "Attempt was not found")
    if user.role == "student" and (
        attempt.lab_id != user.lab_id or attempt.student_id != user.sub
    ):
        raise api_error(404, "ATTEMPT_NOT_FOUND", "Attempt was not found")
    return attempt
