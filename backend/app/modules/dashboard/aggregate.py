from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Student, StudentProfile
from app.schemas.student import ClassDashboardOut, StudentNeedsHelp, WeakTopic


async def class_summary(
    class_id: str,
    teacher_id: str,
    session: AsyncSession,
) -> ClassDashboardOut:
    rows = (
        await session.execute(
            select(Student, StudentProfile)
            .outerjoin(StudentProfile, StudentProfile.student_id == Student.id)
            .where(Student.teacher_id == teacher_id, Student.class_id == class_id)
        )
    ).all()

    scores: list[float] = []
    topic_rates: dict[str, list[float]] = defaultdict(list)
    needs_help: list[StudentNeedsHelp] = []

    for student, profile in rows:
        if profile is None:
            continue

        scores.append(profile.avg_score)
        memory = profile.memory or {}
        for item in memory.get("weak_topics", []):
            topic_rates[item["topic"]].append(item["error_rate"])

        if memory.get("trend") == "regressing" or profile.avg_score < 3.5:
            needs_help.append(
                StudentNeedsHelp(
                    student_id=student.id,
                    reason=(
                        "regressing"
                        if memory.get("trend") == "regressing"
                        else "low_score"
                    ),
                )
            )

    weak_topics = [
        WeakTopic(topic=topic, error_rate=sum(rates) / len(rates))
        for topic, rates in topic_rates.items()
    ]
    weak_topics.sort(key=lambda item: (-item.error_rate, item.topic))

    return ClassDashboardOut(
        class_id=class_id,
        students_count=len(rows),
        avg_score=sum(scores) / len(scores) if scores else 0.0,
        weak_topics=weak_topics[:5],
        students_needing_help=needs_help,
    )
