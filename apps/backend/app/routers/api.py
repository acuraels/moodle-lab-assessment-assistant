"""Compatibility router module exporting the split API routers."""

from app.routers.ai_settings import router as ai_settings_router
from app.routers.files import router as files_router
from app.routers.instructor_attempts import router as instructor_attempts_router
from app.routers.labs import router as labs_router
from app.routers.profile import router as profile_router
from app.routers.student_attempts import router as student_attempts_router
from app.routers.submissions import router as submissions_router

routers = [
    profile_router,
    labs_router,
    ai_settings_router,
    student_attempts_router,
    submissions_router,
    instructor_attempts_router,
    files_router,
]
