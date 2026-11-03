from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.lab import Lab
    from app.models.review import ReviewHistory
    from app.models.stored_file import StoredFile


class AttemptStatus(StrEnum):
    PROCESSING = "processing"
    AI_CHECKED = "ai_checked"
    ACCEPTED = "accepted"
    RETURNED_FOR_REVISION = "returned_for_revision"
    AI_FAILED = "ai_failed"


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[str] = mapped_column(String(255), index=True)
    student_name: Mapped[str] = mapped_column(String(255), index=True)
    academic_group: Mapped[str | None] = mapped_column("Academic_group", String(255), index=True)
    number: Mapped[int] = mapped_column(Integer)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    teacher_submitted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    teacher_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    ai_score: Mapped[float | None] = mapped_column(Float)
    ai_max_score: Mapped[float | None] = mapped_column(Float)
    ai_conclusion: Mapped[str | None] = mapped_column(Text)
    ai_criteria: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON)
    settings_version: Mapped[int | None] = mapped_column(Integer)
    ai_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    teacher_comment: Mapped[str | None] = mapped_column(Text)
    reviewed_by: Mapped[str | None] = mapped_column(String(255))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    lab: Mapped["Lab"] = relationship(back_populates="attempts")
    files: Mapped[list["StoredFile"]] = relationship(back_populates="attempt")
    reviews: Mapped[list["ReviewHistory"]] = relationship(back_populates="attempt")
