from pydantic import BaseModel, ConfigDict


class UserContext(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sub: str
    email: str = ""
    name: str
    role: str
    course_id: str
    lab_id: str
    lab_title: str = ""
    Academic_group: str | None = None
