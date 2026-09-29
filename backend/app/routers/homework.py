from datetime import date, datetime
import re
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.auth import current_teacher
from app.db import get_session
from app.models.homework import Homework
from app.modules.homework.export import render_pdf, render_txt
from app.modules.homework.pipeline import generate_homework, regenerate_homework
from app.schemas.generation import Subject
from app.schemas.homework import HomeworkCreate, HomeworkOut, HomeworkPatch, HomeworkRegenerate


router = APIRouter(prefix="/homework", tags=["homework"])


async def owned_homework(
    homework_id: str, teacher_id: str, session: AsyncSession
) -> Homework:
    hw = await session.get(Homework, homework_id)
    if hw is None:
        raise HTTPException(status_code=404, detail="Домашнее задание не найдено")
    if hw.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Домашнее задание принадлежит другому учителю")
    return hw


@router.post("", response_model=HomeworkOut, response_model_exclude_unset=True, status_code=201)
async def create_homework(
    payload: HomeworkCreate,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    hw = await generate_homework(
        teacher_id, payload.subject, payload.grade, payload.topic,
        payload.n_tasks, payload.prompt,
    )
    if payload.title is not None:
        hw.title = payload.title
    session.add(hw)
    await session.commit()
    await session.refresh(hw)
    return hw


@router.get("", response_model=list[HomeworkOut], response_model_exclude_unset=True)
async def list_homework(
    teacher_id: str = Depends(current_teacher),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    subject: Subject | None = None,
    grade: int | None = Query(default=None, ge=1, le=11),
    topic: str | None = Query(default=None, min_length=1, max_length=200),
    session: AsyncSession = Depends(get_session),
) -> list[Homework]:
    stmt = select(Homework).where(Homework.teacher_id == teacher_id)
    if subject is not None:
        stmt = stmt.where(Homework.subject == subject)
    if grade is not None:
        stmt = stmt.where(Homework.grade == grade)
    if topic is not None:
        if not topic.strip():
            raise HTTPException(status_code=422, detail="Тема не может быть пустой")
        stmt = stmt.where(Homework.topic.icontains(topic.strip(), autoescape=True))
    result = await session.scalars(
        stmt.order_by(Homework.updated_at.desc(), Homework.id).limit(limit).offset(offset)
    )
    return list(result.all())


@router.get("/{homework_id}", response_model=HomeworkOut, response_model_exclude_unset=True)
async def get_homework(
    homework_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    return await owned_homework(homework_id, teacher_id, session)


@router.patch("/{homework_id}", response_model=HomeworkOut, response_model_exclude_unset=True)
async def patch_homework(
    homework_id: str,
    payload: HomeworkPatch,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    hw = await owned_homework(homework_id, teacher_id, session)
    for name, value in payload.model_dump(exclude_unset=True).items():
        setattr(hw, name, value)
    hw.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(hw)
    return hw


@router.post("/{homework_id}/regenerate", response_model=HomeworkOut, response_model_exclude_unset=True)
async def regenerate(
    homework_id: str,
    payload: HomeworkRegenerate | None = None,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    hw = await owned_homework(homework_id, teacher_id, session)
    # Do not mutate the persisted version until the complete new set is valid.
    hw.tasks = await regenerate_homework(hw, payload.extra_prompt if payload else None)
    hw.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(hw)
    return hw


@router.delete("/{homework_id}", status_code=204)
async def delete_homework(
    homework_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    hw = await owned_homework(homework_id, teacher_id, session)
    await session.delete(hw)
    await session.commit()
    return Response(status_code=204)


@router.get("/{homework_id}/export")
async def export_homework(
    homework_id: str,
    format: Literal["txt", "pdf"] = Query(...),
    with_answers: bool = True,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    hw = await owned_homework(homework_id, teacher_id, session)
    title = re.sub(r'[\x00-\x1f\x7f<>:"/\\|?*]', "-", hw.title)
    filename = f"homework-{title}-{date.today():%Y-%m-%d}.{format}"
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", title).strip("-") or "assignment"
    fallback = f"homework-{safe_title}-{date.today():%Y-%m-%d}.{format}"
    renderer = render_txt if format == "txt" else render_pdf
    content = await run_in_threadpool(renderer, hw, with_answers=with_answers)
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8" if format == "txt" else "application/pdf",
        headers={"Content-Disposition": (
            f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"
        )},
    )
