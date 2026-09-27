from datetime import datetime

from pydantic import BaseModel, Field


class PhotoBox(BaseModel):
    photo_index: int
    x: float
    y: float
    w: float
    h: float


class ReasoningStep(BaseModel):
    step: str
    ok: bool


class TeacherVerdict(BaseModel):
    is_correct: bool
    comment: str = ""


class TaskCheck(BaseModel):
    task_index: int
    student_answer: str = ""
    expected_answer: str = ""
    is_correct: bool = False
    confidence: float = 0.0
    explanation: str = ""
    reasoning_graph: list[ReasoningStep] = Field(default_factory=list)
    photo_boxes: list[PhotoBox] = Field(default_factory=list)
    teacher_verdict: TeacherVerdict | None = None


class SubmissionOut(BaseModel):
    id: str
    work_id: str
    student_id: str
    status: str
    created_at: datetime
    photos: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SubmissionResultOut(SubmissionOut):
    per_task: list[TaskCheck] = Field(default_factory=list)
    total_score: float = 0.0
    confidence: float = 0.0


class TeacherReviewItem(BaseModel):
    task_index: int
    is_correct: bool
    comment: str = ""


class TeacherReview(BaseModel):
    per_task: list[TeacherReviewItem]
