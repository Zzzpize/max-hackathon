from io import BytesIO
from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import CheckResult, Student, Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.check.pipeline import run_check
from app.schemas.submission import SubmissionOut, SubmissionResultOut, TeacherReview
from app.modules.memory.update import on_submission_confirmed

router = APIRouter(prefix="/submissions", tags=["submissions"])

MAX_PHOTO_BYTES = 10 * 1024 * 1024
PHOTO_TYPES = {
    "image/jpeg": ("JPEG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/webp": ("WEBP", ".webp"),
}


@router.post("", response_model=SubmissionOut, status_code=202)
async def create_submission(
    background: BackgroundTasks,
    work_id: str = Form(...),
    student_id: str = Form(...),
    photos: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> Submission:
    if not 1 <= len(photos) <= 4:
        raise HTTPException(status_code=422, detail="provide 1 to 4 photos")

    if await session.get(WorkTemplate, work_id) is None:
        raise HTTPException(status_code=404, detail="work not found")
    if await session.get(Student, student_id) is None:
        raise HTTPException(status_code=404, detail="student not found")

    # Проверяем все файлы до записи: не оставляем часть работы,
    # если последнее фото оказалось невалидным.
    validated: list[tuple[bytes, str]] = []
    for photo in photos:
        expected = PHOTO_TYPES.get(photo.content_type or "")
        if expected is None:
            raise HTTPException(status_code=415, detail="unsupported photo type")

        data = await photo.read(MAX_PHOTO_BYTES + 1)
        if not data:
            raise HTTPException(status_code=422, detail="empty photo")
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(status_code=413, detail="photo exceeds 10 MB")

        try:
            with Image.open(BytesIO(data)) as image:
                actual_format = image.format
                image.verify()
        except (OSError, ValueError, SyntaxError) as exc:
            raise HTTPException(
                status_code=415, detail="invalid image"
            ) from exc

        expected_format, extension = expected
        if actual_format != expected_format:
            raise HTTPException(
                status_code=415, detail="photo type does not match content"
            )
        validated.append((data, extension))

    submission_id = str(uuid4())
    storage_root = Path(settings.storage_dir) / submission_id
    saved_paths: list[str] = []

    try:
        storage_root.mkdir(parents=True)
        for index, (data, extension) in enumerate(validated):
            target = storage_root / f"{index}{extension}"
            target.write_bytes(data)
            saved_paths.append(str(target.relative_to(settings.storage_dir)))

        submission = Submission(
            id=submission_id,
            work_id=work_id,
            student_id=student_id,
            status=SubmissionStatus.pending,
            photos=saved_paths,
        )
        session.add(submission)
        await session.commit()
    except Exception:
        shutil.rmtree(storage_root, ignore_errors=True)
        raise

    await session.refresh(submission)
    background.add_task(run_check, submission_id)
    return submission


@router.get("", response_model=list[SubmissionOut])
async def list_submissions(
    teacher_id: str,
    status: SubmissionStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Submission]:
    stmt = (
        select(Submission)
        .join(WorkTemplate, WorkTemplate.id == Submission.work_id)
        .where(WorkTemplate.teacher_id == teacher_id)
    )
    if status is not None:
        stmt = stmt.where(Submission.status == status)

    result = await session.execute(
        stmt.order_by(Submission.created_at.desc(), Submission.id)
    )
    return list(result.scalars().all())


@router.get("/{submission_id}", response_model=SubmissionResultOut)
async def get_submission(
    submission_id: str,
    session: AsyncSession = Depends(get_session),
) -> SubmissionResultOut:
    submission = await session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")

    check = (
        None if submission.status == SubmissionStatus.pending
        else await session.get(CheckResult, submission_id)
    )
    return SubmissionResultOut(
        id=submission.id,
        work_id=submission.work_id,
        student_id=submission.student_id,
        status=submission.status,
        created_at=submission.created_at,
        photos=submission.photos,
        per_task=check.per_task if check else [],
        total_score=check.total_score if check else 0.0,
        confidence=check.confidence if check else 0.0,
    )


@router.patch("/{submission_id}/review")
async def review_submission(
    submission_id: str,
    review: TeacherReview,
    session: AsyncSession = Depends(get_session),
) -> dict:
    submission = await session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")
    if submission.status not in (SubmissionStatus.checked, SubmissionStatus.confirmed):
        raise HTTPException(status_code=409, detail="submission is not checked")
    already_confirmed = submission.status == SubmissionStatus.confirmed

    check = await session.get(CheckResult, submission_id)
    if check is None:
        raise HTTPException(status_code=409, detail="not yet checked")

    verdict_by_task = {item.task_index: item for item in review.per_task}
    updated = []
    for task in check.per_task:
        verdict = verdict_by_task.get(task["task_index"])
        if verdict is not None:
            task = {
                **task,
                "teacher_verdict": {
                    "is_correct": verdict.is_correct,
                    "comment": verdict.comment,
                },
            }
        updated.append(task)
    check.per_task = updated

    submission.status = SubmissionStatus.confirmed
    if not already_confirmed:
        await on_submission_confirmed(submission_id, session)
    await session.commit()

    return {"status": "ok"}
