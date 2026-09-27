import logging
from pathlib import Path

from app.config import settings
from app.db import SessionLocal
from app.llm.gigachat import gigachat_client
from app.models import CheckResult, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.check.prompts import CHECK_TASK_SYSTEM, RECOGNIZE_ANSWERS_SYSTEM

logger = logging.getLogger(__name__)


async def run_check(submission_id: str) -> None:
    """Асинхронный пайплайн проверки одной работы.

    Шаги:
    1. Загрузить фото и шаблон работы.
    2. VLM: распознать ответы ученика по каждому заданию.
    3. LLM: сверить с эталоном, объяснить ошибку, построить граф решения.
    4. Сохранить CheckResult, отметить submission как checked.
    """
    async with SessionLocal() as session:
        submission = await session.get(Submission, submission_id)
        if submission is None:
            logger.warning("submission %s not found", submission_id)
            return

        work = await session.get(WorkTemplate, submission.work_id)
        if work is None:
            logger.warning("work %s not found", submission.work_id)
            return

        photo_paths = [
            Path(settings.storage_dir) / p for p in submission.photos
        ]

        recognized = await gigachat_client.recognize_answers(
            photos=photo_paths,
            system_prompt=RECOGNIZE_ANSWERS_SYSTEM,
        )

        per_task: list[dict] = []
        total_score = 0.0
        confidences: list[float] = []

        for task in work.tasks:
            idx = task["index"]
            student_answer = ""
            recognition_conf = 0.0
            for r in recognized:
                if r.get("task_index") == idx:
                    student_answer = r.get("answer", "")
                    recognition_conf = float(r.get("confidence", 0.0))
                    break

            verdict = await gigachat_client.check_task(
                system_prompt=CHECK_TASK_SYSTEM,
                statement=task["statement"],
                expected_answer=task["expected_answer"],
                student_answer=student_answer,
            )

            is_correct = bool(verdict.get("correct", False))
            per_task.append(
                {
                    "task_index": idx,
                    "student_answer": student_answer,
                    "expected_answer": task["expected_answer"],
                    "is_correct": is_correct,
                    "confidence": recognition_conf,
                    "explanation": verdict.get("explanation", ""),
                    "reasoning_graph": verdict.get("reasoning_graph", []),
                    "photo_boxes": [],
                    "teacher_verdict": None,
                }
            )
            if is_correct:
                total_score += float(task.get("max_points", 1))
            confidences.append(recognition_conf)

        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        existing = await session.get(CheckResult, submission_id)
        if existing is None:
            session.add(
                CheckResult(
                    submission_id=submission_id,
                    per_task=per_task,
                    total_score=total_score,
                    confidence=avg_conf,
                )
            )
        else:
            existing.per_task = per_task
            existing.total_score = total_score
            existing.confidence = avg_conf

        submission.status = SubmissionStatus.checked
        await session.commit()
