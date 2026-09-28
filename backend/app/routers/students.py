import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.modules.memory.profile import build_profile
from app.schemas.student import StudentCreate, StudentOut, StudentProfileOut

from app.config import settings
from app.models import CheckResult, Student, StudentProfile, Submission
from app.student_names import get_name, name_hash, save_name

router = APIRouter(prefix="/students", tags=["students"])
logger = logging.getLogger(__name__)

@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    payload: StudentCreate,
    session: AsyncSession = Depends(get_session),
    teacher_id: str = Depends(current_teacher),
) -> StudentOut:
    student_id = str(uuid4())
    student = Student(
        id=student_id, teacher_id=teacher_id, class_id=payload.class_id,
        display_name=name_hash(student_id, payload.display_name), grade=payload.grade,
    )
    save_name(teacher_id, student.id, payload.display_name)
    session.add(student)
    try:
        await session.commit()
    except Exception:
        save_name(teacher_id, student.id, None)
        raise
    await session.refresh(student)
    return StudentOut.model_validate(student).model_copy(update={"display_name": payload.display_name})


@router.get("", response_model=list[StudentOut])
async def list_students(
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> list[StudentOut]:
    result = await session.scalars(
        select(Student).where(Student.teacher_id == teacher_id).order_by(Student.created_at, Student.id)
    )
    return [
        StudentOut.model_validate(student).model_copy(update={
            "display_name": get_name(teacher_id, student.id, student.display_name)
        })
        for student in result.all()
    ]


@router.delete("/{student_id}", status_code=204)
async def delete_student(
    student_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with session.begin():
        student = await session.get(Student, student_id, with_for_update=True)
        if student is None:
            raise HTTPException(status_code=404, detail="student not found")
        if student.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="student belongs to another teacher")

        submission_ids = list((
            await session.scalars(
                select(Submission.id).where(Submission.student_id == student_id)
            )
        ).all())

        if any(
            Path(submission_id).name != submission_id or submission_id in (".", "..")
            for submission_id in submission_ids
        ):
            raise HTTPException(status_code=500, detail="invalid submission id")

        if submission_ids:
            await session.execute(
                delete(CheckResult).where(CheckResult.submission_id.in_(submission_ids))
            )
            await session.execute(
                delete(Submission).where(Submission.id.in_(submission_ids))
            )

        await session.execute(
            delete(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        await session.delete(student)

    storage = Path(settings.storage_dir)
    cleanup_failed = False
    for submission_id in submission_ids:
        try:
            shutil.rmtree(storage / submission_id)
        except FileNotFoundError:
            pass
        except OSError:
            logger.exception("Photo cleanup failed for submission %s", submission_id)
            cleanup_failed = True

    save_name(teacher_id, student_id, None)
    if cleanup_failed:
        raise HTTPException(status_code=500, detail="student deleted but photo cleanup failed")

    return Response(status_code=204)

@router.get("/{student_id}/profile", response_model=StudentProfileOut)
async def get_profile(
    student_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> StudentProfileOut:
    student = await session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="student not found")
    if student.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="student belongs to another teacher")
    profile = await build_profile(session, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="student not found")
    return profile
