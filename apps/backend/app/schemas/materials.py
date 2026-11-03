from pydantic import BaseModel


class MaterialInput(BaseModel):
    text: str | None = None
    file_id: str | None = None


class AISettingsInput(BaseModel):
    methodical_guide: MaterialInput | None = None
    grading_criteria: MaterialInput | None = None
    system_instructions: MaterialInput | None = None
    reference_work: MaterialInput | None = None
