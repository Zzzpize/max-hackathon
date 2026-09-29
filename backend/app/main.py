import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import Base, engine, get_session
from app.models import Submission, WorkTemplate
from app.models.submission import SubmissionStatus
from app.modules.check.queue import worker
from app.routers import stats, students, submissions, teachers, works, roadmaps, homework


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.dev_auto_create_tables:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    check_worker = asyncio.create_task(worker())
    try:
        yield
    finally:
        check_worker.cancel()
        with suppress(asyncio.CancelledError):
            await check_worker


app = FastAPI(
    title="Помощник учителя API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(works.router)
app.include_router(submissions.router)
app.include_router(students.router)
app.include_router(stats.router)
app.include_router(teachers.router)
app.include_router(roadmaps.router)
app.include_router(homework.router)

storage_root = Path(settings.storage_dir)
storage_root.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_root)), name="storage")


class BotNotifyEvent(BaseModel):
    teacher_id: str
    event: str
    submission_id: str


@app.post("/internal/bot/notify", include_in_schema=False)
async def bot_notify(event: BotNotifyEvent, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    if event.event != "submission_checked":
        raise HTTPException(status_code=422, detail="unsupported event")
    submission = await session.get(Submission, event.submission_id)
    work = await session.get(WorkTemplate, submission.work_id) if submission else None
    if submission is None or work is None or work.teacher_id != event.teacher_id:
        raise HTTPException(status_code=404, detail="submission not found")
    if submission.status not in (SubmissionStatus.checked, SubmissionStatus.confirmed):
        raise HTTPException(status_code=409, detail="submission is not checked")
    return {"status": "ok"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
