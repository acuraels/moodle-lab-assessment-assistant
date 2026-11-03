from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import api_error
from app.middleware.session import UserContext, get_current_user
from app.models import Attempt, FilePurpose, StoredFile

router = APIRouter(prefix="/api", tags=["files"])


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stored = await db.get(StoredFile, file_id)
    if stored is None or stored.lab_id != user.lab_id:
        raise api_error(404, "FILE_NOT_FOUND", "File was not found")
    if user.role == "student" and stored.purpose == FilePurpose.AI_SETTING:
        raise api_error(404, "FILE_NOT_FOUND", "File was not found")
    if stored.attempt_id:
        attempt = await db.get(Attempt, stored.attempt_id)
        if user.role == "student" and (
            attempt is None or attempt.student_id != user.sub
        ):
            raise api_error(404, "FILE_NOT_FOUND", "File was not found")
    return Response(
        content=stored.data,
        media_type=stored.content_type,
        headers={"Content-Disposition": f'attachment; filename="{stored.filename}"'},
    )
