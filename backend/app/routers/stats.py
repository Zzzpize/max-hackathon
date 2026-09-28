from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.models import Student, StudentProfile
from app.schemas.student import ClassDashboardOut, StudentNeedsHelp, WeakTopic

router = APIRouter(prefix="/classes", tags=["stats"])


@router.get("/{class_id}/dashboard", response_model=ClassDashboardOut)
async def class_dashboard(
    class_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> ClassDashboardOut:
    rows = (await session.execute(
        select(Student, StudentProfile)
        .outerjoin(StudentProfile, StudentProfile.student_id == Student.id)
        .where(Student.teacher_id == teacher_id, Student.class_id == class_id)
    )).all()
    topics: dict[str, list[float]] = defaultdict(list)
    needs_help = []
    scores = []
    for student, profile in rows:
        if profile is None:
            continue
        scores.append(profile.avg_score)
        memory = profile.memory or {}
        for topic in memory.get("weak_topics", []):
            topics[topic["topic"]].append(topic["error_rate"])
        if memory.get("trend") == "regressing" or profile.avg_score < 3.5:
            needs_help.append(StudentNeedsHelp(
                student_id=student.id,
                reason="regressing" if memory.get("trend") == "regressing" else "low_score",
            ))
    return ClassDashboardOut(
        class_id=class_id,
        students_count=len(rows),
        avg_score=sum(scores) / len(scores) if scores else 0.0,
        weak_topics=sorted(
            (WeakTopic(topic=name, error_rate=sum(rates) / len(rates)) for name, rates in topics.items()),
            key=lambda topic: -topic.error_rate,
        )[:5],
        students_needing_help=needs_help,
    )
