from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SubmissionStatus(StrEnum):
    pending = "pending"
    checked = "checked"
    confirmed = "confirmed"


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    work_id: Mapped[str] = mapped_column(String, ForeignKey("work_templates.id"))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("students.id"))
    status: Mapped[str] = mapped_column(String, default=SubmissionStatus.pending)
    photos: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    result: Mapped["CheckResult | None"] = relationship(
        back_populates="submission", uselist=False, cascade="all, delete-orphan"
    )


class CheckResult(Base):
    __tablename__ = "check_results"

    submission_id: Mapped[str] = mapped_column(
        String, ForeignKey("submissions.id"), primary_key=True
    )
    per_task: Mapped[list] = mapped_column(JSONB, default=list)
    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    submission: Mapped[Submission] = relationship(back_populates="result")
