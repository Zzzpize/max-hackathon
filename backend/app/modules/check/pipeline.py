import logging
import httpx
from pathlib import Path

from app.config import settings
from app.db import SessionLocal
from app.llm.gigachat import gigachat_client
from app.models import CheckResult, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.check.prompts import CHECK_TASK_SYSTEM, RECOGNIZE_ANSWERS_SYSTEM

logger = logging.getLogger(__name__)


async def run_check(submission_id: str) -> None:
    try:
        async with SessionLocal() as session:
            submission = await session.get(Submission, submission_id)
            if submission is None:
                logger.warning("submission %s not found", submission_id)
                return
            if submission.status == SubmissionStatus.confirmed:
                return

            work = await session.get(WorkTemplate, submission.work_id)
            if work is None:
                raise ValueError(f"work {submission.work_id} not found")

            recognized = await gigachat_client.recognize_answers(
                photos=[
                    Path(settings.storage_dir) / photo
                    for photo in submission.photos
                ],
                system_prompt=RECOGNIZE_ANSWERS_SYSTEM,
            )
            answers = {item["task_index"]: item for item in recognized}

            per_task = []
            total_score = 0.0
            confidences = []

            for task in work.tasks:
                answer = answers.get(task["index"], {})
                student_answer = answer.get("answer", "")
                confidence = float(answer.get("confidence", 0.0))

                if confidence < 0.5:
                    student_answer = ""
                    verdict = {
                        "correct": False,
                        "explanation": "Требуется ручная проверка",
                        "reasoning_graph": [],
                    }
                else:
                    verdict = await gigachat_client.check_task(
                        system_prompt=CHECK_TASK_SYSTEM,
                        statement=task["statement"],
                        expected_answer=task["expected_answer"],
                        student_answer=student_answer,
                    )

                is_correct = bool(verdict["correct"])

                per_task.append({
                    "task_index": task["index"],
                    "student_answer": student_answer,
                    "expected_answer": task["expected_answer"],
                    "is_correct": is_correct,
                    "confidence": confidence,
                    "explanation": verdict["explanation"],
                    "reasoning_graph": verdict["reasoning_graph"],
                    "photo_boxes": [],
                    "teacher_verdict": None,
                })
                if is_correct:
                    total_score += float(task.get("max_points", 1))
                confidences.append(confidence)

            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.0
            )

            result = await session.get(CheckResult, submission_id)
            if result is None:
                result = CheckResult(submission_id=submission_id)
                session.add(result)

            result.per_task = per_task
            result.total_score = total_score
            result.confidence = avg_confidence
            submission.status = SubmissionStatus.checked
            await session.commit()
            
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.post(
                        settings.bot_notify_url,
                        json={
                            "teacher_id": work.teacher_id,
                            "event": "submission_checked",
                            "submission_id": submission_id,
                        },
                    )
                    response.raise_for_status()
            except httpx.HTTPError:
                logger.exception("bot notification failed for %s", submission_id)
    
    
    except Exception:
        logger.exception("check failed for submission %s", submission_id)
        raise