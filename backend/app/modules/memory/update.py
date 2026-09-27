from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StudentProfile, Submission
from app.modules.memory.profile import build_profile


async def on_submission_confirmed(submission_id: str, session: AsyncSession) -> None:
    submission = await session.get(Submission, submission_id)
    if submission is None:
        raise ValueError(f"submission {submission_id} not found")

    profile = await build_profile(session, submission.student_id)
    if profile is None:
        raise ValueError(f"student {submission.student_id} not found")

    saved = await session.get(StudentProfile, profile.student_id)
    if saved is None:
        saved = StudentProfile(student_id=profile.student_id)
        session.add(saved)
    saved.submissions_count = profile.submissions_count
    saved.avg_score = profile.avg_score
    saved.memory = {
        "weak_topics": [topic.model_dump() for topic in profile.weak_topics],
        "recurring_mistakes": profile.recurring_mistakes,
        "trend": profile.trend,
    }
    saved.updated_at = datetime.utcnow()
