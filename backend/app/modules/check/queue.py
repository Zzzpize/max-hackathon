"""Redis-backed queue for submission checks. Run one worker per deployment."""

import asyncio
import logging

from redis.asyncio import Redis
from sqlalchemy import select

from app.config import settings
from app.db import SessionLocal
from app.models import Submission
from app.models.submission import SubmissionStatus
from app.modules.check.pipeline import run_check

logger = logging.getLogger(__name__)
QUEUE = "check:pending"
PROCESSING = "check:processing"


async def enqueue_check(submission_id: str) -> None:
    async with Redis.from_url(settings.redis_url, decode_responses=True) as redis:
        await redis.lpush(QUEUE, submission_id)


async def _work_once() -> None:
    async with Redis.from_url(settings.redis_url, decode_responses=True) as redis:
        # Requeue work left by a stopped worker, then recover committed submissions
        # that could not be enqueued while Redis was unavailable.
        while job := await redis.rpoplpush(PROCESSING, QUEUE):
            logger.info("requeued interrupted check %s", job)
        async with SessionLocal() as session:
            pending = await session.scalars(
                select(Submission.id).where(Submission.status == SubmissionStatus.pending)
            )
            for submission_id in pending:
                await redis.lpush(QUEUE, submission_id)

        while True:
            submission_id = await redis.brpoplpush(QUEUE, PROCESSING, timeout=5)
            if submission_id is None:
                continue
            try:
                await run_check(submission_id)
            except Exception:
                logger.exception("check job failed for %s", submission_id)
            finally:
                await redis.lrem(PROCESSING, 1, submission_id)


async def worker() -> None:
    while True:
        try:
            await _work_once()
        except Exception:
            logger.exception("Check worker stopped; reconnecting")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(worker())
