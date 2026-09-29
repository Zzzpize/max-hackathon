from datetime import datetime
import re
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.models import Roadmap
from app.modules.roadmap.export import render_pdf, render_txt
from app.modules.roadmap.pipeline import generate_roadmap, regenerate_segment, validate_content


router = APIRouter(prefix="/roadmaps", tags=["roadmaps"])

Subject = Literal["math", "algebra", "physics", "geometry"]


class RoadmapCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    subject: Subject
    grade: int = Field(ge=1, le=11)
    prompt: str = Field(min_length=10, max_length=2000)


class RoadmapPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=120)
    content: dict | None = None


class SegmentRegenerate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    refine_prompt: str = Field(min_length=1, max_length=2000)


class RoadmapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    teacher_id: str
    title: str
    subject: Subject
    grade: int
    prompt: str
    content: dict
    created_at: datetime
    updated_at: datetime


async def owned_roadmap(
    roadmap_id: str, teacher_id: str, session: AsyncSession
) -> Roadmap:
    roadmap = await session.scalar(
        select(Roadmap).where(
            Roadmap.id == roadmap_id,
            Roadmap.teacher_id == teacher_id,
        )
    )
    if roadmap is None:
        raise HTTPException(status_code=404, detail="Роадмап не найден")
    return roadmap


@router.post("", response_model=RoadmapOut, status_code=201)
async def create_roadmap(
    payload: RoadmapCreate,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Roadmap:
    roadmap = await generate_roadmap(
        teacher_id, payload.subject, payload.grade, payload.prompt
    )
    if payload.title is not None:
        roadmap.title = payload.title

    session.add(roadmap)
    await session.commit()
    await session.refresh(roadmap)
    return roadmap


@router.get("", response_model=list[RoadmapOut])
async def list_roadmaps(
    teacher_id: str = Depends(current_teacher),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[Roadmap]:
    result = await session.scalars(
        select(Roadmap)
        .where(Roadmap.teacher_id == teacher_id)
        .order_by(Roadmap.updated_at.desc(), Roadmap.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.all())


@router.get("/{roadmap_id}", response_model=RoadmapOut)
async def get_roadmap(
    roadmap_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Roadmap:
    return await owned_roadmap(roadmap_id, teacher_id, session)


@router.patch("/{roadmap_id}", response_model=RoadmapOut)
async def patch_roadmap(
    roadmap_id: str,
    payload: RoadmapPatch,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Roadmap:
    if not payload.model_fields_set:
        raise HTTPException(status_code=422, detail="Укажите title или content")

    roadmap = await owned_roadmap(roadmap_id, teacher_id, session)

    if "title" in payload.model_fields_set:
        if payload.title is None:
            raise HTTPException(status_code=422, detail="title не может быть null")
        roadmap.title = payload.title

    if "content" in payload.model_fields_set:
        if payload.content is None:
            raise HTTPException(status_code=422, detail="content не может быть null")

        # Редактор MiniApp может добавить сегмент без materials_hint.
        # Пустая строка соответствует отсутствию указанных материалов.
        content = payload.content
        segments = content.get("segments")
        if isinstance(segments, list):
            content = {
                **content,
                "segments": [
                    {"materials_hint": "", **segment}
                    if isinstance(segment, dict) else segment
                    for segment in segments
                ],
            }
        try:
            roadmap.content = validate_content(content)
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    roadmap.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(roadmap)
    return roadmap


@router.delete("/{roadmap_id}", status_code=204)
async def delete_roadmap(
    roadmap_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> None:
    roadmap = await owned_roadmap(roadmap_id, teacher_id, session)
    await session.delete(roadmap)
    await session.commit()


@router.patch("/{roadmap_id}/segments/{index}", response_model=RoadmapOut)
async def patch_segment(
    roadmap_id: str,
    index: int,
    payload: SegmentRegenerate,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Roadmap:
    roadmap = await owned_roadmap(roadmap_id, teacher_id, session)
    roadmap.content = await regenerate_segment(roadmap, index, payload.refine_prompt)
    roadmap.updated_at = datetime.utcnow()
    await session.commit()
    await session.refresh(roadmap)
    return roadmap


@router.get("/{roadmap_id}/export")
async def export_roadmap(
    roadmap_id: str,
    format: Literal["txt", "pdf"] = Query(...),
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> Response:
    roadmap = await owned_roadmap(roadmap_id, teacher_id, session)
    filename = f"roadmap-{roadmap.title}-{roadmap.created_at:%Y-%m-%d}.{format}"
    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "-", roadmap.title).strip("-") or "plan"
    fallback = f"roadmap-{safe_title}-{roadmap.created_at:%Y-%m-%d}.{format}"
    return Response(
        content=render_txt(roadmap) if format == "txt" else render_pdf(roadmap),
        media_type="text/plain; charset=utf-8" if format == "txt" else "application/pdf",
        headers={"Content-Disposition": (
            f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{quote(filename, safe='')}"
        )},
    )
