from typing import Literal

from datetime import datetime

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    class_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    grade: int


class StudentOut(StudentCreate):
    id: str
    teacher_id: str
    created_at: datetime

    model_config = {"from_attributes": True}


class WeakTopic(BaseModel):
    topic: str
    error_rate: float


class StudentProfileOut(BaseModel):
    student_id: str
    submissions_count: int
    avg_score: float
    weak_topics: list[WeakTopic] = Field(default_factory=list)
    recurring_mistakes: list[str] = Field(default_factory=list)
    trend: Literal["improving", "stable", "regressing"] = "stable"


class StudentNeedsHelp(BaseModel):
    student_id: str
    reason: str


class ClassDashboardOut(BaseModel):
    class_id: str
    students_count: int
    avg_score: float
    weak_topics: list[WeakTopic] = Field(default_factory=list)
    students_needing_help: list[StudentNeedsHelp] = Field(default_factory=list)
