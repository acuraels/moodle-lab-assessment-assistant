from pathlib import PurePath
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.errors import api_error
from app.middleware.session import UserContext, require_instructor
from app.models import AISettings, FilePurpose, StoredFile
from app.schemas.materials import AISettingsInput
from app.routers.common import get_lab, now
from app.services.files import ALLOWED_SETTING_TYPES, read_upload

router = APIRouter(prefix="/api", tags=["ai-settings"])
MATERIAL_FIELDS = {
    "methodical_guide",
    "grading_criteria",
    "system_instructions",
    "reference_work",
}


def material_value(material):
    if material is None:
        return None
    if material.text is not None and material.file_id is not None:
        raise api_error(400, "INVALID_MATERIAL", "Material must contain text or file_id, not both")
    if material.text is None and material.file_id is None:
        raise api_error(400, "INVALID_MATERIAL", "Material must contain text or file_id")
    return material


async def _file_metadata(
    db: AsyncSession,
    file_id: str | None,
    lab_id: str,
) -> dict | None:
    if file_id is None:
        return None
    stored = await db.scalar(
        select(StoredFile).where(
            StoredFile.id == file_id,
            StoredFile.lab_id == lab_id,
            StoredFile.purpose == FilePurpose.AI_SETTING,
        )
    )
    if stored is None:
        return None
    return {
        "file_id": stored.id,
        "name": stored.filename,
        "size": stored.size,
        "content_type": stored.content_type,
        "download_url": f"/api/files/{stored.id}/download",
    }


async def _material_response(
    db: AsyncSession,
    lab_id: str,
    text: str | None,
    file_id: str | None,
) -> dict | None:
    if text is None and file_id is None:
        return None
    return {
        "text": text,
        "file": await _file_metadata(db, file_id, lab_id),
    }


@router.get("/labs/{lab_id}/ai-settings")
async def read_ai_settings(
    lab_id: str,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lab = await get_lab(db, lab_id, user)
    settings_row = await db.get(AISettings, lab.id)
    if settings_row is None:
        return {
            "lab_id": lab.id,
            "version": 0,
            "settings_status": "not_configured",
            "updated_at": None,
            "methodical_guide": None,
            "grading_criteria": None,
            "system_instructions": None,
            "reference_work": None,
        }
    return {
        "lab_id": lab.id,
        "version": settings_row.version,
        "settings_status": "configured",
        "updated_at": settings_row.updated_at,
        "methodical_guide": await _material_response(
            db,
            lab.id,
            settings_row.methodical_guide_text,
            settings_row.methodical_guide_file_id,
        ),
        "grading_criteria": await _material_response(
            db,
            lab.id,
            settings_row.grading_criteria_text,
            settings_row.grading_criteria_file_id,
        ),
        "system_instructions": await _material_response(
            db,
            lab.id,
            settings_row.system_instructions_text,
            settings_row.system_instructions_file_id,
        ),
        "reference_work": await _material_response(
            db,
            lab.id,
            settings_row.reference_work_text,
            settings_row.reference_work_file_id,
        ),
    }


@router.post("/labs/{lab_id}/ai-settings/files", status_code=201)
async def upload_ai_file(
    lab_id: str,
    field: str = Form(...),
    file: UploadFile = File(...),
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lab = await get_lab(db, lab_id, user)
    if field not in MATERIAL_FIELDS:
        raise api_error(400, "INVALID_FIELD", "Unknown AI settings field")
    try:
        data = await read_upload(file, ALLOWED_SETTING_TYPES)
    except ValueError as exc:
        code = str(exc)
        raise api_error(413 if code == "FILE_TOO_LARGE" else 415, code, code)
    stored = StoredFile(
        id=str(uuid4()),
        lab_id=lab.id,
        purpose=FilePurpose.AI_SETTING,
        field=field,
        filename=PurePath(file.filename or "upload").name,
        content_type=file.content_type or "application/octet-stream",
        size=len(data),
        data=data,
        created_at=now(),
    )
    db.add(stored)
    await db.commit()
    return {
        "file_id": stored.id,
        "field": field,
        "name": stored.filename,
        "size": stored.size,
        "content_type": stored.content_type,
    }


@router.put("/labs/{lab_id}/ai-settings")
async def save_ai_settings(
    lab_id: str,
    payload: AISettingsInput,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lab = await get_lab(db, lab_id, user)
    values = {
        name: material_value(getattr(payload, name))
        for name in MATERIAL_FIELDS
    }
    if not any(value is not None for value in values.values()):
        raise api_error(400, "SETTINGS_EMPTY", "At least one AI material is required")
    for value in values.values():
        if value and value.file_id:
            stored = await db.get(StoredFile, value.file_id)
            if stored is None or stored.lab_id != lab.id or stored.purpose != FilePurpose.AI_SETTING:
                raise api_error(404, "FILE_NOT_FOUND", "AI settings file was not found")
    settings_row = await db.get(AISettings, lab.id)
    if settings_row is None:
        settings_row = AISettings(lab_id=lab.id, version=1, updated_at=now())
        db.add(settings_row)
    else:
        settings_row.version += 1
        settings_row.updated_at = now()
    for name, value in values.items():
        setattr(settings_row, f"{name}_text", value.text if value else None)
        setattr(settings_row, f"{name}_file_id", value.file_id if value else None)
    await db.commit()
    return {
        "lab_id": lab.id,
        "version": settings_row.version,
        "settings_status": "configured",
        "updated_at": settings_row.updated_at,
    }


@router.delete("/labs/{lab_id}/ai-settings/{field}")
async def delete_ai_material(
    lab_id: str,
    field: str,
    user: UserContext = Depends(require_instructor),
    db: AsyncSession = Depends(get_db),
):
    lab = await get_lab(db, lab_id, user)
    if field not in MATERIAL_FIELDS:
        raise api_error(400, "INVALID_FIELD", "Unknown AI settings field")
    settings_row = await db.get(AISettings, lab.id)
    if settings_row:
        setattr(settings_row, f"{field}_text", None)
        setattr(settings_row, f"{field}_file_id", None)
        settings_row.version += 1
        settings_row.updated_at = now()
        await db.commit()
    return Response(status_code=204)
