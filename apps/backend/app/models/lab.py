from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.ai_settings import AISettings
    from app.models.attempt import Attempt
    from app.models.stored_file import StoredFile


class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = (UniqueConstraint("course_id", "resource_link_id"),)

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    course_id: Mapped[str] = mapped_column(String(255), index=True)
    resource_link_id: Mapped[str] = mapped_column(String(255), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts_limit: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    settings: Mapped["AISettings | None"] = relationship(back_populates="lab", uselist=False)
    files: Mapped[list["StoredFile"]] = relationship(back_populates="lab")
    attempts: Mapped[list["Attempt"]] = relationship(back_populates="lab")
