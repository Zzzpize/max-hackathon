from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.models import Student, TeacherState, WorkTemplate

router = APIRouter(prefix="/teachers", tags=["teachers"])


class TeacherStateOut(BaseModel):
    teacher_id: str
    current_work_id: str | None = None
    current_student_id: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class TeacherStatePatch(BaseModel):
    current_work_id: str | None = None
    current_student_id: str | None = None


async def _load_state(
    session: AsyncSession, teacher_id: str
) -> TeacherState:
    state = await session.get(TeacherState, teacher_id)
    if state is None:
        state = TeacherState(teacher_id=teacher_id)
        session.add(state)
    return state


@router.get("/me/state", response_model=TeacherStateOut)
async def get_state(
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> TeacherStateOut:
    state = await session.get(TeacherState, teacher_id)
    if state is None:
        return TeacherStateOut(teacher_id=teacher_id)
    return TeacherStateOut.model_validate(state)


@router.put("/me/state", response_model=TeacherStateOut)
async def set_state(
    payload: TeacherStatePatch,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> TeacherStateOut:
    """Partial update: только явно переданные поля меняются.

    - Поле не в body → не трогаем существующее значение.
    - Поле = null в body → сбрасываем (снятие выбора).
    """
    changes = payload.model_dump(exclude_unset=True)

    if changes.get("current_work_id"):
        work = await session.get(WorkTemplate, changes["current_work_id"])
        if work is None:
            raise HTTPException(status_code=404, detail="work not found")
        if work.teacher_id != teacher_id:
            raise HTTPException(
                status_code=403, detail="work belongs to another teacher"
            )

    if changes.get("current_student_id"):
        student = await session.get(Student, changes["current_student_id"])
        if student is None:
            raise HTTPException(status_code=404, detail="student not found")
        if student.teacher_id != teacher_id:
            raise HTTPException(
                status_code=403, detail="student belongs to another teacher"
            )

    state = await _load_state(session, teacher_id)
    if "current_work_id" in changes:
        state.current_work_id = changes["current_work_id"]
    if "current_student_id" in changes:
        state.current_student_id = changes["current_student_id"]
    await session.commit()
    await session.refresh(state)
    return TeacherStateOut.model_validate(state)
