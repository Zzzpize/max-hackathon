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
ATTEMPTS = "check:attempts"  # hash submission_id -> attempt count

MAX_ATTEMPTS = 8
BASE_BACKOFF_SECONDS = 15


async def enqueue_check(submission_id: str) -> None:
    async with Redis.from_url(settings.redis_url, decode_responses=True) as redis:
        await redis.hdel(ATTEMPTS, submission_id)
        await redis.lpush(QUEUE, submission_id)


async def _delayed_requeue(submission_id: str, delay: float) -> None:
    await asyncio.sleep(delay)
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
            failed = False
            try:
                await run_check(submission_id)
            except Exception:
                failed = True
                logger.exception("check job failed for %s", submission_id)
            finally:
                await redis.lrem(PROCESSING, 1, submission_id)

            if not failed:
                await redis.hdel(ATTEMPTS, submission_id)
                continue

            attempts = await redis.hincrby(ATTEMPTS, submission_id, 1)
            if attempts >= MAX_ATTEMPTS:
                logger.error(
                    "giving up on submission %s after %s attempts", submission_id, attempts
                )
                await redis.hdel(ATTEMPTS, submission_id)
                continue

            # Экспоненциальный бэкофф: 15с, 30с, 60с, 120с... до 30 минут.
            delay = min(BASE_BACKOFF_SECONDS * (2 ** (attempts - 1)), 1800)
            logger.warning(
                "retrying submission %s in %.0fs (attempt %s/%s)",
                submission_id, delay, attempts, MAX_ATTEMPTS,
            )
            asyncio.create_task(_delayed_requeue(submission_id, delay))


async def worker() -> None:
    while True:
        try:
            await _work_once()
        except Exception:
            logger.exception("Check worker stopped; reconnecting")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(worker())
