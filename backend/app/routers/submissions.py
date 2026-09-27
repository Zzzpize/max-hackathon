import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_session
from app.models import CheckResult, Submission
from app.models.submission import SubmissionStatus
from app.modules.check.pipeline import run_check
from app.schemas.submission import SubmissionOut, SubmissionResultOut, TeacherReview

router = APIRouter(prefix="/submissions", tags=["submissions"])


@router.post("", response_model=SubmissionOut, status_code=202)
async def create_submission(
    background: BackgroundTasks,
    work_id: str = Form(...),
    student_id: str = Form(...),
    photos: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> Submission:
    submission_id = str(uuid4())
    storage_root = Path(settings.storage_dir) / submission_id
    storage_root.mkdir(parents=True, exist_ok=True)

    saved_paths: list[str] = []
    for idx, photo in enumerate(photos):
        ext = os.path.splitext(photo.filename or "")[1] or ".jpg"
        target = storage_root / f"{idx}{ext}"
        with target.open("wb") as f:
            f.write(await photo.read())
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
    await session.refresh(submission)

    background.add_task(run_check, submission_id)
    return submission


@router.get("", response_model=list[SubmissionOut])
async def list_submissions(
    teacher_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Submission]:
    # TODO(backend): join через work_templates.teacher_id
    stmt = select(Submission)
    if status:
        stmt = stmt.where(Submission.status == status)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{submission_id}", response_model=SubmissionResultOut)
async def get_submission(
    submission_id: str,
    session: AsyncSession = Depends(get_session),
) -> SubmissionResultOut:
    submission = await session.get(Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="submission not found")

    check = await session.get(CheckResult, submission_id)
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

    check = await session.get(CheckResult, submission_id)
    if check is None:
        raise HTTPException(status_code=409, detail="not yet checked")

    verdict_by_task = {item.task_index: item for item in review.per_task}
    updated = []
    for task in check.per_task:
        v = verdict_by_task.get(task["task_index"])
        if v is not None:
            task["teacher_verdict"] = {"is_correct": v.is_correct, "comment": v.comment}
        updated.append(task)
    check.per_task = updated

    submission.status = SubmissionStatus.confirmed
    await session.commit()

    # TODO(backend): триггер обновления профиля ученика (memory module)
    return {"status": "ok"}
