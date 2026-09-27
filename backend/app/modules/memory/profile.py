from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.gigachat import gigachat_client
from app.models import CheckResult, Student, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.memory.prompts import RECURRING_MISTAKES_SYSTEM
from app.schemas.student import StudentProfileOut, WeakTopic


async def build_profile(
    session: AsyncSession, student_id: str
) -> StudentProfileOut | None:
    if await session.get(Student, student_id) is None:
        return None

    result = await session.execute(
        select(Submission, CheckResult, WorkTemplate)
        .join(CheckResult, CheckResult.submission_id == Submission.id)
        .join(WorkTemplate, WorkTemplate.id == Submission.work_id)
        .where(
            Submission.student_id == student_id,
            Submission.status == SubmissionStatus.confirmed,
        )
        .order_by(Submission.created_at.desc(), Submission.id.desc())
    )
    submissions = result.all()

    # Значения: [неправильных задач, проверенных задач].
    topics = defaultdict(lambda: [0, 0])
    scores = []
    recent_explanations = []

    for index, (_, check, work) in enumerate(submissions):
        points_by_task = {
            task["index"]: float(task.get("max_points", 1))
            for task in work.tasks
        }
        score = 0.0

        for task in check.per_task:
            verdict = task.get("teacher_verdict")
            if not isinstance(verdict, dict):
                continue

            is_correct = verdict["is_correct"]
            topics[work.title][1] += 1
            if is_correct:
                score += points_by_task.get(task["task_index"], 1.0)
            else:
                topics[work.title][0] += 1
                if index < 10:
                    explanation = (
                        verdict.get("comment") or task.get("explanation") or ""
                    ).strip()
                    if explanation:
                        recent_explanations.append(explanation)

        scores.append(score)

    weak_topics = [
        WeakTopic(topic=title, error_rate=wrong / reviewed)
        for title, (wrong, reviewed) in topics.items()
        if reviewed and wrong
    ]
    weak_topics.sort(key=lambda item: (-item.error_rate, item.topic))

    mistakes = await gigachat_client.summarize_mistakes(
        recent_explanations, RECURRING_MISTAKES_SYSTEM
    )

    return StudentProfileOut(
        student_id=student_id,
        submissions_count=len(submissions),
        avg_score=sum(scores) / len(scores) if scores else 0.0,
        weak_topics=weak_topics,
        recurring_mistakes=mistakes,
        trend="stable",  # Расчёт тренда — отдельный пункт 11.
    )