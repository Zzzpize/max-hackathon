import logging
import shutil
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_teacher
from app.db import get_session
from app.llm.gigachat import gigachat_client
from app.models import WorkTemplate
from app.modules.check.prompts import EXTRACT_REFERENCE_SYSTEM
from app.modules.generate.pipeline import generate_work
from app.schemas.work import WorkTemplateCreate, WorkTemplateOut

router = APIRouter(prefix="/works", tags=["works"])
logger = logging.getLogger(__name__)

EXTRACT_MAX_BYTES = 20 * 1024 * 1024
EXTRACT_ACCEPTED = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
PDF_PAGE_LIMIT = 20
PDF_DPI = 150


@router.post("", response_model=WorkTemplateOut, status_code=201)
async def create_work(
    payload: WorkTemplateCreate,
    session: AsyncSession = Depends(get_session),
    teacher_id: str = Depends(current_teacher),
) -> WorkTemplate:
    work = WorkTemplate(
        teacher_id=teacher_id,
        title=payload.title,
        subject=payload.subject,
        grade=payload.grade,
        tasks=[task.model_dump() for task in payload.tasks],
    )
    session.add(work)
    await session.commit()
    await session.refresh(work)
    return work


@router.get("", response_model=list[WorkTemplateOut])
async def list_works(
    teacher_id: str = Depends(current_teacher),
    limit: int = Query(default=50, ge=1),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> list[WorkTemplate]:
    result = await session.execute(
        select(WorkTemplate)
        .where(WorkTemplate.teacher_id == teacher_id)
        .order_by(WorkTemplate.created_at, WorkTemplate.id)
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


class GenerateWorkRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(min_length=1, max_length=120)
    grade: Literal[2, 3, 4]
    n_tasks: int = Field(ge=1, le=20)


@router.post("/generate", response_model=WorkTemplateOut, status_code=201)
async def create_generated_work(
    payload: GenerateWorkRequest,
    session: AsyncSession = Depends(get_session),
    teacher_id: str = Depends(current_teacher),
) -> WorkTemplate:
    work = await generate_work(payload.topic, payload.grade, payload.n_tasks)
    work.teacher_id = teacher_id
    session.add(work)
    await session.commit()
    await session.refresh(work)
    return work


class ExtractedTask(BaseModel):
    index: str
    statement: str
    expected_answer: str
    confidence: float


class ExtractReferenceOut(BaseModel):
    title: str = ""
    subject: str | None = None
    grade: int | None = None
    tasks: list[ExtractedTask]


def _pdf_to_images(pdf_bytes: bytes, workdir: Path) -> list[Path]:
    """Rasterize each PDF page into a JPEG. Uses PyMuPDF (no system deps)."""
    import fitz  # PyMuPDF

    paths: list[Path] = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        pages = min(len(doc), PDF_PAGE_LIMIT)
        for page_index in range(pages):
            page = doc.load_page(page_index)
            pix = page.get_pixmap(dpi=PDF_DPI)
            target = workdir / f"page-{page_index:03d}.jpg"
            pix.save(str(target))
            paths.append(target)
    return paths


def _validate_image(data: bytes) -> None:
    from io import BytesIO
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
    except (OSError, ValueError, SyntaxError) as exc:
        raise HTTPException(status_code=415, detail="invalid image") from exc


@router.post("/extract-reference", response_model=ExtractReferenceOut)
async def extract_reference(
    file: UploadFile = File(...),
    _teacher_id: str = Depends(current_teacher),
) -> ExtractReferenceOut:
    """Извлечь задания и эталоны из PDF или фото учительского материала."""
    ext = EXTRACT_ACCEPTED.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=415, detail="only JPEG, PNG, WEBP or PDF is accepted"
        )
    data = await file.read(EXTRACT_MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    if len(data) > EXTRACT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds 20 MB")

    workdir = Path(tempfile.mkdtemp(prefix="ref-"))
    try:
        if ext == ".pdf":
            try:
                image_paths = _pdf_to_images(data, workdir)
            except Exception as exc:
                logger.exception("PDF rasterization failed")
                raise HTTPException(status_code=422, detail="cannot read PDF") from exc
            if not image_paths:
                raise HTTPException(status_code=422, detail="empty PDF")
        else:
            _validate_image(data)
            image_path = workdir / f"input{ext}"
            image_path.write_bytes(data)
            image_paths = [image_path]

        extracted = await gigachat_client.extract_reference(
            photos=image_paths,
            system_prompt=EXTRACT_REFERENCE_SYSTEM,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    return ExtractReferenceOut(
        title=extracted.get("title", ""),
        subject=extracted.get("subject"),
        grade=extracted.get("grade"),
        tasks=[ExtractedTask(**task) for task in extracted.get("tasks", [])],
    )


@router.get("/{work_id}", response_model=WorkTemplateOut)
async def get_work(
    work_id: str,
    teacher_id: str = Depends(current_teacher),
    session: AsyncSession = Depends(get_session),
) -> WorkTemplate:
    work = await session.get(WorkTemplate, work_id)
    if work is None:
        raise HTTPException(status_code=404, detail="work not found")
    if work.teacher_id != teacher_id:
        raise HTTPException(status_code=403, detail="work belongs to another teacher")
    return work
