import logging
import re
import httpx
from pathlib import Path

from app.config import settings
from app.db import SessionLocal
from app.llm.gigachat import gigachat_client
from app.models import CheckResult, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.check.prompts import CHECK_TASK_SYSTEM, RECOGNIZE_ANSWERS_SYSTEM

logger = logging.getLogger(__name__)

_NORMALIZE = re.compile(r"[\s.,;]+")


def _normalize_answer(text: str) -> str:
    """Свернуть пробелы и разделители — 'Ответ: 68 ' и '68' сравнятся равными."""
    return _NORMALIZE.sub("", text.strip().lower().replace(" ", ""))


async def run_check(submission_id: str) -> None:
    try:
        async with SessionLocal() as session:
            submission = await session.get(Submission, submission_id)
            if submission is None:
                logger.warning("submission %s not found", submission_id)
                return
            if submission.status != SubmissionStatus.pending:
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
                tasks=[
                    {"index": task["index"], "statement": task["statement"]}
                    for task in work.tasks
                ],
            )
            for item in recognized:
                logger.warning(
                    "recognize %s: task=%s answer=%r raw_context=%r boxes=%s",
                    submission_id, item.get("task_index"),
                    item.get("answer"), item.get("raw_context"),
                    len(item.get("photo_boxes") or []),
                )
            answers = {item["task_index"]: item for item in recognized}

            # GigaChat Freemium физлицам разрешает только 1 поток генерации.
            # Параллельные LLM-вызовы получают 429 — идём последовательно.
            # Оффлайн-шорткаты (не распознано, точный матч) остаются мгновенными.
            resolved: list[tuple[dict, dict, float]] = []
            for task in work.tasks:
                answer = answers.get(task["index"], {})
                student_answer = answer.get("answer", "")
                confidence = float(answer.get("confidence", 0.0))
                raw_context = str(answer.get("raw_context", ""))

                not_recognized = {
                    "correct": False,
                    "explanation": "Требуется ручная проверка",
                    "reasoning_graph": [],
                    "error_type": "не распознано",
                }

                if confidence < 0.5 or not student_answer.strip():
                    resolved.append((answer, not_recognized, 0.0))
                    continue

                # Anti-hallucination guard #1: если модель не смогла указать
                # где именно на фото находится ответ (photo_boxes пустой) —
                # почти наверняка ответа там нет, а модель его додумала.
                photo_boxes = answer.get("photo_boxes") or []
                if not photo_boxes:
                    logger.warning(
                        "recognize hallucination guard: task %s answer %r has no photo_boxes",
                        task["index"], student_answer,
                    )
                    resolved.append((answer, not_recognized, 0.0))
                    continue

                # Anti-hallucination guard #2: answer должен быть подстрокой того,
                # что модель заявила как raw_context. Если модель сгенерировала
                # ответ из головы (например, "8 пирожков" из «Всего: 48 п.») —
                # честный raw_context не содержал бы этот ответ.
                if raw_context and _normalize_answer(student_answer) not in _normalize_answer(raw_context):
                    logger.warning(
                        "recognize hallucination guard: task %s answer %r not in raw_context %r",
                        task["index"], student_answer, raw_context,
                    )
                    resolved.append((answer, not_recognized, 0.0))
                    continue

                if _normalize_answer(student_answer) == _normalize_answer(task["expected_answer"]):
                    verdict = {
                        "correct": True,
                        "explanation": "Верно!",
                        "reasoning_graph": [],
                        "error_type": None,
                    }
                    resolved.append((answer, verdict, confidence))
                    continue

                verdict = await gigachat_client.check_task(
                    system_prompt=CHECK_TASK_SYSTEM,
                    statement=task["statement"],
                    expected_answer=task["expected_answer"],
                    student_answer=student_answer,
                )
                resolved.append((answer, verdict, confidence))

            per_task = []
            total_score = 0.0
            confidences = []

            for task, (answer, verdict, confidence) in zip(work.tasks, resolved):
                student_answer = (
                    ""
                    if verdict.get("error_type") == "не распознано"
                    else answer.get("answer", "")
                )
                is_correct = bool(verdict["correct"])

                per_task.append({
                    "task_index": task["index"],
                    "student_answer": student_answer,
                    "expected_answer": task["expected_answer"],
                    "is_correct": is_correct,
                    "confidence": confidence,
                    "explanation": verdict["explanation"],
                    "error_type": verdict.get("error_type"),
                    "reasoning_graph": verdict["reasoning_graph"],
                    "photo_boxes": answer.get("photo_boxes") or [],
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
