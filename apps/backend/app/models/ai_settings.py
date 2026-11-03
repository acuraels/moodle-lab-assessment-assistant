from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.lab import Lab


class AISettings(Base):
    __tablename__ = "ai_settings"

    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    methodical_guide_text: Mapped[str | None] = mapped_column(Text)
    methodical_guide_file_id: Mapped[str | None] = mapped_column(String(128))
    grading_criteria_text: Mapped[str | None] = mapped_column(Text)
    grading_criteria_file_id: Mapped[str | None] = mapped_column(String(128))
    system_instructions_text: Mapped[str | None] = mapped_column(Text)
    system_instructions_file_id: Mapped[str | None] = mapped_column(String(128))
    reference_work_text: Mapped[str | None] = mapped_column(Text)
    reference_work_file_id: Mapped[str | None] = mapped_column(String(128))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lab: Mapped["Lab"] = relationship(back_populates="settings")
