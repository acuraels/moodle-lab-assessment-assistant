from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.attempt import Attempt
    from app.models.lab import Lab


class FilePurpose(StrEnum):
    AI_SETTING = "ai_setting"
    ATTEMPT = "attempt"


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    lab_id: Mapped[str] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), index=True)
    attempt_id: Mapped[str | None] = mapped_column(ForeignKey("attempts.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str] = mapped_column(String(32))
    field: Mapped[str | None] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(128))
    size: Mapped[int] = mapped_column(Integer)
    data: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    lab: Mapped["Lab"] = relationship(back_populates="files")
    attempt: Mapped["Attempt | None"] = relationship(back_populates="files")
