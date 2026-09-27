from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.modules.memory.profile import build_profile
from app.schemas.student import StudentProfileOut

router = APIRouter(prefix="/students", tags=["students"])


@router.get("/{student_id}/profile", response_model=StudentProfileOut)
async def get_profile(
    student_id: str,
    session: AsyncSession = Depends(get_session),
) -> StudentProfileOut:
    profile = await build_profile(session, student_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="student not found")
    return profile
