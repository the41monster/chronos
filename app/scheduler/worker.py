import asyncio
import logging
import uuid
from datetime import datetime, timezone

from croniter import croniter
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.enums import ExecutionStatus, JobStatus, ScheduleType
from app.models.job import Job
from app.models.job_execution import JobExecution

logger = logging.getLogger(__name__)


async def _execute_job(
    session_factory: async_sessionmaker,
    job_id: uuid.UUID,
    execution_id: uuid.UUID
) -> None:
    async with session_factory() as db:
        job = await db.get(Job, job_id)
        execution = await db.get(JobExecution, execution_id)

        if not job or not execution:
            return
        
        try:
            # Placeholder for actual job execution logic based on job.job_type and job.payload
            log_output = f"Job {job.id} ({job.job_type}) executed successfully"

            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = datetime.now(timezone.utc)
            execution.log_output = log_output

            if job.schedule_type == ScheduleType.RECURRING and job.recurrence_pattern:
                cron = croniter(job.recurrence_pattern, datetime.now(timezone.utc))
                job.execution_time = cron.get_next(datetime)
                job.status = JobStatus.SCHEDULED
            else:
                job.status = JobStatus.COMPLETED
            
            await db.commit()
            logger.info("Job %s completed", job.id)
        
        except Exception as e:
            execution.status = ExecutionStatus.FAILURE
            execution.completed_at = datetime.now(timezone.utc)
            execution.error_message = str(e)
            job.status = JobStatus.FAILED
            await db.commit()
            logger.error("Job %s failed", job.id)
            raise


async def worker(session_factory: async_sessionmaker, queue: asyncio.Queue) -> None:
    while True:
        job_id, execution_id = await queue.get()
        try:
            await _execute_job(session_factory, job_id, execution_id)
        except Exception:
            logger.exception("Worker error for job %s", job_id)
        finally:
            queue.task_done()
