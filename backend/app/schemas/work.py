from datetime import datetime
from typing import Self


from pydantic import BaseModel, Field, field_validator, model_validator


class TaskDefinition(BaseModel):
    index: int
    statement: str
    expected_answer: str
    max_points: float = 1.0

    @field_validator("expected_answer")
    @classmethod
    def answer_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("expected_answer must not be empty")
        return value



class WorkTemplateCreate(BaseModel):
    teacher_id: str
    title: str
    subject: str = "math"
    grade: int
    tasks: list[TaskDefinition] = Field(default_factory=list)

    @model_validator(mode="after")
    def task_indexes_must_be_unique(self) -> Self:
        indexes = [task.index for task in self.tasks]
        if len(indexes) != len(set(indexes)):
            raise ValueError("Task indexes must be unique")
        return self


class WorkTemplateOut(WorkTemplateCreate):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True
