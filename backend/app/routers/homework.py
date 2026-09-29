from datetime import datetime
import re
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.models import Homework
from app.modules.generate.core import validate_tasks
from app.modules.generate import core
from app.modules.homework.export import render_pdf, render_txt
from app.modules.homework.pipeline import generate_homework

router = APIRouter(prefix="/homework", tags=["homework"])
Subject = Literal["math", "algebra", "physics", "geometry"]


class HomeworkCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    subject: Subject
    grade: int = Field(ge=1, le=11)
    topic: str = Field(min_length=1, max_length=200)
    n_tasks: int = Field(ge=1, le=30)
    prompt: str = Field(min_length=5, max_length=2000)


class HomeworkPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = None
    tasks: list[dict] | None = Field(default=None, min_length=1, max_length=30)

    @field_validator("tasks")
    @classmethod
    def check_tasks(cls, value: list[dict] | None) -> list[dict] | None:
        if value is None:
            return None
        return validate_tasks(value, len(value))


class HomeworkRegenerate(BaseModel):
    extra_prompt: str = ""


class HomeworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    teacher_id: str
    title: str
    subject: Subject
    grade: int
    topic: str
    prompt: str
    tasks: list[dict]
    notes: str | None
    created_at: datetime
    updated_at: datetime


async def owned_homework(homework_id: str, teacher_id: str, session: AsyncSession) -> Homework:
    homework = await session.get(Homework, homework_id)
    if homework is None:
        raise HTTPException(status_code=404, detail="Домашка не найдена")
    if homework.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="Домашка другого учителя")
    return homework


@router.post("", response_model=HomeworkOut, status_code=201)
async def create_homework(
    payload: HomeworkCreate,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    homework = await generate_homework(
        teacher_id, payload.subject, payload.grade, payload.topic,
        payload.n_tasks, payload.prompt, payload.title,
    )
    session.add(homework)
    await session.commit()
    await session.refresh(homework)
    return homework


@router.get("", response_model=list[HomeworkOut])
async def list_homework(
    teacher_id: str = Depends(current_teacher),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    subject: Subject | None = None,
    grade: int | None = Query(default=None, ge=1, le=11),
    topic: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[Homework]:
    query = select(Homework).where(Homework.teacher_id == teacher_id)
    if subject is not None:
        query = query.where(Homework.subject == subject)
    if grade is not None:
        query = query.where(Homework.grade == grade)
    if topic:
        search = topic.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Homework.topic.ilike(f"%{search}%", escape="\\"))
    result = await session.scalars(
        query.order_by(Homework.updated_at.desc(), Homework.id).limit(limit).offset(offset)
    )
    return list(result.all())


@router.get("/{homework_id}", response_model=HomeworkOut)
async def get_homework(
    homework_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    return await owned_homework(homework_id, teacher_id, session)


@router.patch("/{homework_id}", response_model=HomeworkOut)
async def patch_homework(
    homework_id: str,
    payload: HomeworkPatch,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    if not payload.model_fields_set:
        raise HTTPException(status_code=422, detail="Нет изменений")
    homework = await owned_homework(homework_id, teacher_id, session)
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        if value is None and field != "notes":
            raise HTTPException(status_code=422, detail=f"{field} не может быть null")
        setattr(homework, field, value)
    homework.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(homework)
    return homework


@router.delete("/{homework_id}", status_code=204)
async def delete_homework(
    homework_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> None:
    homework = await owned_homework(homework_id, teacher_id, session)
    await session.delete(homework)
    await session.commit()


@router.post("/{homework_id}/regenerate", response_model=HomeworkOut)
async def regenerate_homework(
    homework_id: str,
    payload: HomeworkRegenerate,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Homework:
    homework = await owned_homework(homework_id, teacher_id, session)
    context = "\n".join(part for part in (homework.prompt, payload.extra_prompt.strip()) if part)
    homework.tasks = await core.generate_tasks(
        homework.subject, homework.grade, homework.topic, len(homework.tasks), context
    )
    homework.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(homework)
    return homework


@router.get("/{homework_id}/export")
async def export_homework(
    homework_id: str,
    format: Literal["txt", "pdf"] = Query(...),
    with_answers: bool = True,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    homework = await owned_homework(homework_id, teacher_id, session)
    filename = f"homework-{homework.title}-{homework.created_at:%Y-%m-%d}.{format}"
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", homework.title).strip("-") or "homework"
    fallback = f"homework-{safe_title}-{homework.created_at:%Y-%m-%d}.{format}"
    return Response(
        content=(render_txt(homework, with_answers=with_answers) if format == "txt"
                 else render_pdf(homework, with_answers=with_answers)),
        media_type="text/plain; charset=utf-8" if format == "txt" else "application/pdf",
        headers={"Content-Disposition": (
            f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"
        )},
    )
