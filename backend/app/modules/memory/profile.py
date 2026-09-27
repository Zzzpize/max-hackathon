from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CheckResult, Student, Submission
from app.models.submission import SubmissionStatus
from app.schemas.student import StudentProfileOut


async def build_profile(
    session: AsyncSession, student_id: str
) -> StudentProfileOut | None:
    """Собирает долгосрочный профиль ученика по истории submissions.

    MVP: агрегация по confirmed. Позже - кластеризация ошибок через LLM,
    выявление тренда (improving / regressing).
    """
    student = await session.get(Student, student_id)
    if student is None:
        return None

    rows = await session.execute(
        select(Submission, CheckResult)
        .join(CheckResult, CheckResult.submission_id == Submission.id)
        .where(
            Submission.student_id == student_id,
            Submission.status == SubmissionStatus.confirmed,
        )
        .order_by(Submission.created_at.desc())
    )

    submissions = list(rows.all())
    count = len(submissions)
    if count == 0:
        return StudentProfileOut(
            student_id=student_id,
            submissions_count=0,
            avg_score=0.0,
        )

    total_score = sum(r.total_score for _, r in submissions)

    # TODO(memory module): извлечь recurring mistakes через LLM-суммаризацию
    return StudentProfileOut(
        student_id=student_id,
        submissions_count=count,
        avg_score=total_score / count,
        weak_topics=[],
        recurring_mistakes=[],
        trend="stable",
    )
