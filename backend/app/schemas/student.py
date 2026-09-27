from typing import Literal

from pydantic import BaseModel, Field


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
