import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.modules.memory.profile import build_profile
from app.schemas.student import StudentCreate, StudentOut, StudentProfileOut

from app.config import settings
from app.models import CheckResult, Student, StudentProfile, Submission

router = APIRouter(prefix="/students", tags=["students"])

@router.post("", response_model=StudentOut, status_code=201)
async def create_student(
    payload: StudentCreate,
    session: AsyncSession = Depends(get_session),
    teacher_id: str = Depends(current_teacher),
) -> Student:
    student = Student(**payload.model_dump(), teacher_id=teacher_id)
    session.add(student)
    await session.commit()
    await session.refresh(student)
    return student


@router.get("", response_model=list[StudentOut])
async def list_students(
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> list[Student]:
    result = await session.scalars(
        select(Student).where(Student.teacher_id == teacher_id).order_by(Student.created_at, Student.id)
    )
    return list(result.all())


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
    for submission_id in submission_ids:
        shutil.rmtree(storage / str(UUID(submission_id)), ignore_errors=True)

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
