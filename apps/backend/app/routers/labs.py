from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.session import UserContext, get_current_user
from app.routers.common import get_lab

router = APIRouter(prefix="/api", tags=["labs"])


@router.get("/labs/{lab_id}")
async def read_lab(
    lab_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lab = await get_lab(db, lab_id, user)
    response = {
        "id": lab.id,
        "title": lab.title,
        "description": lab.description,
        "deadline": lab.deadline,
        "attempts_limit": lab.attempts_limit,
    }
    if user.role == "instructor":
        response["course_id"] = lab.course_id
    return response
