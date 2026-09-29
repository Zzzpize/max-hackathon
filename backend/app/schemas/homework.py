from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.generation import GeneratedTask, Subject


class HomeworkCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    subject: Subject
    grade: int = Field(ge=1, le=11, strict=True)
    topic: str = Field(min_length=1, max_length=200)
    n_tasks: int = Field(ge=1, le=30, strict=True)
    prompt: str = Field(min_length=5, max_length=2000)


class HomeworkPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    tasks: list[GeneratedTask] | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("tasks")
    @classmethod
    def task_indexes_must_be_sequential(
        cls, tasks: list[GeneratedTask] | None
    ) -> list[GeneratedTask] | None:
        if tasks is not None and [task.index for task in tasks] != list(range(1, len(tasks) + 1)):
            raise ValueError("Номера задач должны идти от 1 без повторов и пропусков")
        return tasks

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Укажите title, notes или tasks")
        for name in ("title", "tasks"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} не может быть null")
        return self


class HomeworkRegenerate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    extra_prompt: str | None = Field(default=None, max_length=2000)


class HomeworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    teacher_id: str
    title: str
    subject: Subject
    grade: int
    topic: str
    prompt: str
    tasks: list[GeneratedTask]
    notes: str | None
    created_at: datetime
    updated_at: datetime
