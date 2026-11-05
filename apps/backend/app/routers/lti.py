from datetime import datetime, timezone
from urllib.parse import quote
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.middleware.session import create_token
from app.models.lab import Lab
from app.services.lti import verify_lti_request

router = APIRouter(tags=["lti"])


def _role(raw_roles: str) -> str:
    roles = {value.strip().lower() for value in raw_roles.split(",")}
    if "instructor" in roles or "administrator" in roles:
        return "instructor"
    if "learner" in roles or "student" in roles:
        return "student"
    raise ValueError("unsupported role")


def _parse_deadline(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


@router.post("/lti/launch")
async def lti_launch(request: Request):
    form = await request.form()
    values = [(key, value) for key, value in form.multi_items() if isinstance(value, str)]
    try:
        verify_lti_request(request, values)
    except ValueError as exc:
        return JSONResponse(status_code=403, content={"error": {"code": "LTI_VERIFICATION_FAILED", "message": str(exc)}})
    try:
        required = ("user_id", "roles", "context_id", "resource_link_id", "lis_person_name_full")
        missing = [key for key in required if not form.get(key)]
        if missing:
            raise ValueError(f"missing LTI fields: {', '.join(missing)}")
        role = _role(str(form["roles"]))
        deadline = _parse_deadline(str(form["custom_deadline"])) if form.get("custom_deadline") else None
        attempts_limit = int(str(form["custom_attempts_limit"])) if form.get("custom_attempts_limit") else None
        if attempts_limit is not None and attempts_limit < 1:
            raise ValueError("custom_attempts_limit must be positive")
    except (ValueError, TypeError, OverflowError) as exc:
        code = "UNSUPPORTED_ROLE" if "role" in str(exc) else "INVALID_LTI_REQUEST"
        status = 403 if code == "UNSUPPORTED_ROLE" else 400
        return JSONResponse(status_code=status, content={"error": {"code": code, "message": str(exc)}})

    lab_id = str(uuid5(NAMESPACE_URL, f"{form['context_id']}:{form['resource_link_id']}"))
    now = datetime.now(timezone.utc)
    async with SessionLocal() as db:
        lab = await db.scalar(
            select(Lab).where(
                Lab.course_id == str(form["context_id"]),
                Lab.resource_link_id == str(form["resource_link_id"]),
            )
        )
        if lab is None:
            lab = Lab(
                id=lab_id,
                course_id=str(form["context_id"]),
                resource_link_id=str(form["resource_link_id"]),
                title=str(form.get("resource_link_title") or "Лабораторная работа"),
                description=None,
                deadline=deadline,
                attempts_limit=attempts_limit,
                created_at=now,
                updated_at=now,
            )
            db.add(lab)
        else:
            lab.title = str(form.get("resource_link_title") or lab.title)
            lab.deadline = deadline
            lab.attempts_limit = attempts_limit
            lab.updated_at = now
        lab_id = lab.id
        await db.commit()

    token = create_token(
        {
            "sub": str(form["user_id"]),
            "email": str(form.get("lis_person_contact_email_primary") or ""),
            "name": str(form["lis_person_name_full"]),
            "role": role,
            "course_id": str(form["context_id"]),
            "lab_id": lab_id,
            "lab_title": str(form.get("resource_link_title") or "Лабораторная работа"),
            "Academic_group": str(form.get("Academic_group")) if form.get("Academic_group") else None,
        }
    )
    return RedirectResponse(
        f"{settings.frontend_url}?token={quote(token)}&lab_id={quote(lab_id)}",
        status_code=302,
    )
