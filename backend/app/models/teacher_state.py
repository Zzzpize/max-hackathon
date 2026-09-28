from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class TeacherState(Base):
    __tablename__ = "teacher_states"

    teacher_id: Mapped[str] = mapped_column(String, primary_key=True)
    current_work_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("work_templates.id", ondelete="SET NULL"), nullable=True
    )
    current_student_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("students.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
