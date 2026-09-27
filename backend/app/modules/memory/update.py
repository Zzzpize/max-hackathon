from datetime import datetime

from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import StudentProfile
from app.modules.memory.profile import build_profile


async def on_submission_confirmed(submission_id: str) -> None:
    from app.models import Submission

    async with SessionLocal() as session:
        submission = await session.get(Submission, submission_id)
        if submission is None:
            raise ValueError(f"submission {submission_id} not found")

        profile = await build_profile(session, submission.student_id)
        if profile is None:
            raise ValueError(f"student {submission.student_id} not found")

        values = {
            "student_id": profile.student_id,
            "submissions_count": profile.submissions_count,
            "avg_score": profile.avg_score,
            "memory": {
                "weak_topics": [
                    topic.model_dump() for topic in profile.weak_topics
                ],
                "recurring_mistakes": profile.recurring_mistakes,
                "trend": profile.trend,
            },
            "updated_at": datetime.utcnow(),
        }
        stmt = insert(StudentProfile).values(**values)
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=[StudentProfile.student_id],
                set_={key: value for key, value in values.items()
                      if key != "student_id"},
            )
        )
        await session.commit()