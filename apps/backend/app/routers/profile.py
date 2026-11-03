from fastapi import APIRouter, Depends

from app.middleware.session import UserContext, get_current_user

router = APIRouter(prefix="/api", tags=["profile"])


@router.get("/me")
async def me(user: UserContext = Depends(get_current_user)):
    return {
        "id": user.sub,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "course_id": user.course_id,
        "Academic_group": user.Academic_group,
    }
