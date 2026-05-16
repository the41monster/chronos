import asyncio
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.enums import ExecutionStatus, JobStatus
from app.models.job import Job
from app.models.job_execution import JobExecution

logger = logging.getLogger(__name__)


async def _dispatch_due_jobs(session_factory: async_sessionmaker, queue: asyncio.Queue) -> None:
    dispatched: list[tuple[uuid.UUID, uuid.UUID]] = []

    async with session_factory() as db:
        result = await db.execute(
            select(Job)
            .where(
                Job.status == JobStatus.SCHEDULED,
                Job.execution_time <= datetime.now(timezone.utc)
            )
            .with_for_update(skip_locked=True)
            .limit(10)
        )
        jobs = result.scalars().all()

        executions = []
        for job in jobs:
            job.status = JobStatus.RUNNING
            execution = JobExecution(
                job_id=job.id,
                started_at=datetime.now(timezone.utc),
                status=ExecutionStatus.RUNNING,
                retry_count=job.retry_count
            )
            db.add(execution)
            executions.append((job, execution))
        
        await db.flush()

        for job, execution in executions:
            dispatched.append((job.id, execution.id))
            logger.info("Dispatching job %s", job.id)

        await db.commit()
    
    for job_id, execution_id in dispatched:
        await queue.put((job_id, execution_id))


async def poll(session_factory: async_sessionmaker, queue: asyncio.Queue, poll_interval: int) -> None:
    while True:
        try:
            await _dispatch_due_jobs(session_factory, queue)
        except Exception:
            logger.exception("Scheduler poll error")
        await asyncio.sleep(poll_interval)
