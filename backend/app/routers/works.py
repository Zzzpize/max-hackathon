from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import WorkTemplate
from app.schemas.work import WorkTemplateCreate, WorkTemplateOut

router = APIRouter(prefix="/works", tags=["works"])


@router.post("", response_model=WorkTemplateOut, status_code=201)
async def create_work(
    payload: WorkTemplateCreate,
    session: AsyncSession = Depends(get_session),
) -> WorkTemplate:
    work = WorkTemplate(
        teacher_id=payload.teacher_id,
        title=payload.title,
        subject=payload.subject,
        grade=payload.grade,
        tasks=[t.model_dump() for t in payload.tasks],
    )
    session.add(work)
    await session.commit()
    await session.refresh(work)
    return work


@router.get("", response_model=list[WorkTemplateOut])
async def list_works(
    teacher_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[WorkTemplate]:
    result = await session.execute(
        select(WorkTemplate).where(WorkTemplate.teacher_id == teacher_id)
    )
    return list(result.scalars().all())


@router.get("/{work_id}", response_model=WorkTemplateOut)
async def get_work(
    work_id: str,
    session: AsyncSession = Depends(get_session),
) -> WorkTemplate:
    work = await session.get(WorkTemplate, work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="work not found")
    return work
