"""Freeze material references before the upload transaction commits."""

from app.models import AISettings, Lab


MATERIAL_FIELDS = (
    "methodical_guide", "grading_criteria", "system_instructions", "reference_work",
)


def settings_snapshot(lab: Lab, settings_row: AISettings | None) -> dict | None:
    if settings_row is None:
        return None
    materials = {}
    for field in MATERIAL_FIELDS:
        text = getattr(settings_row, f"{field}_text")
        file_id = getattr(settings_row, f"{field}_file_id")
        if text is not None and text.strip():
            materials[field] = {"text": text}
        elif file_id:
            materials[field] = {"file_id": file_id}
    if not materials:
        return None
    return {
        "lab_id": lab.id,
        "title": lab.title,
        "description": lab.description,
        "settings_version": settings_row.version,
        "materials": materials,
    }
