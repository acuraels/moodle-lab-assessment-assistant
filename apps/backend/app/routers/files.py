import re
import unicodedata
from pathlib import PurePath
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import api_error
from app.middleware.session import UserContext, get_current_user
from app.models import Attempt, FilePurpose, StoredFile

router = APIRouter(prefix="/api", tags=["files"])


def _content_disposition(filename: str) -> str:
    normalized = unicodedata.normalize("NFKD", filename)
    fallback = normalized.encode("ascii", "ignore").decode("ascii")
    fallback = re.sub(r"[^A-Za-z0-9._-]+", "_", fallback).strip("._")
    if not fallback:
        suffix = PurePath(filename).suffix
        fallback = f"download{suffix}" if suffix.isascii() else "download"
    encoded_name = quote(filename, safe="")
    return f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{encoded_name}'


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
        headers={"Content-Disposition": _content_disposition(stored.filename)},
    )
