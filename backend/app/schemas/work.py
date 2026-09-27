from datetime import datetime

from pydantic import BaseModel, Field


class TaskDefinition(BaseModel):
    index: int
    statement: str
    expected_answer: str
    max_points: float = 1.0


class WorkTemplateCreate(BaseModel):
    teacher_id: str
    title: str
    subject: str = "math"
    grade: int
    tasks: list[TaskDefinition] = Field(default_factory=list)


class WorkTemplateOut(WorkTemplateCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
