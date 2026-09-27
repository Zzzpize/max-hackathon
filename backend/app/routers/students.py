import shutil
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.memory.profile import build_profile
from app.schemas.student import StudentProfileOut

from app.config import settings
from app.models import CheckResult, Student, StudentProfile, Submission

router = APIRouter(prefix="/students", tags=["students"])

@router.delete("/{student_id}", status_code=204, include_in_schema=False)
async def delete_student(
    student_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    async with session.begin():
        student = await session.get(Student, student_id, with_for_update=True)
        if student is None:
            raise HTTPException(status_code=404, detail="student not found")

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
    session: AsyncSession = Depends(get_session),
) -> StudentProfileOut:
    profile = await build_profile(session, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="student not found")
    return profile
