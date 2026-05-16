import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from croniter import croniter
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.email import send_failure_email
from app.models.enums import ExecutionStatus, JobStatus, JobType, ScheduleType
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.models.user import User

logger = logging.getLogger(__name__)


async def _run_script(payload: dict) -> str:
    script_path = payload.get("script_path")
    if not script_path:
        raise ValueError("payload must include 'script_path'")
    args = [str(a) for a in payload.get("args", [])]
    env = {**os.environ, **payload.get("env", {})}

    proc = await asyncio.create_subprocess_exec(
        "python", script_path, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env
    )
    stdout, _ = await proc.communicate()
    log_output = stdout.decode()

    if proc.returncode != 0:
        raise RuntimeError(f"Script exited with code {proc.returncode}: \n{log_output}")
    return log_output


async def _run_api_call(payload: dict) -> str:
    url = payload.get("url")
    if not url:
        raise ValueError("payload must include 'url'")
    method = payload.get("method", "GET").upper()
    headers = payload.get("headers", {})
    body = payload.get("body", None)

    async with httpx.AsyncClient() as client:
        response = await client.request(method, url, headers=headers, json=body)
        log_output = f"Status: {response.status_code}\nResponse: {response.text}"
        if response.is_error:
            raise RuntimeError(log_output)
    return log_output


async def _run_data_process(_payload: dict) -> str:
    logger.info("data_process not yet implemented")
    return "data_process: not implemented (stub)"


async def _dispatch(job_type: JobType, payload: dict) -> str:
    if job_type == JobType.SCRIPT:
        return await _run_script(payload)
    if job_type == JobType.API_CALL:
        return await _run_api_call(payload)
    if job_type == JobType.DATA_PROCESS:
        return await _run_data_process(payload)
    raise ValueError(f"Unknown job type: {job_type}")


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
        job_type = job.job_type
        payload = job.payload
        schedule_type = job.schedule_type
        recurrence_pattern = job.recurrence_pattern
        
    try:
        log_output = await _dispatch(job_type, payload)
        async with session_factory() as db:
            job = await db.get(Job, job_id)
            execution = await db.get(JobExecution, execution_id)
            execution.status = ExecutionStatus.SUCCESS
            execution.completed_at = datetime.now(timezone.utc)
            execution.log_output = log_output
            if schedule_type == ScheduleType.RECURRING and recurrence_pattern:
                cron = croniter(recurrence_pattern, datetime.now(timezone.utc))
                job.execution_time = cron.get_next(datetime)
                job.status = JobStatus.SCHEDULED
                job.retry_count = 0
            else:
                job.status = JobStatus.COMPLETED
            await db.commit()
            logger.info("Job %s completed", job.id)
    
    except Exception as e:
        async with session_factory() as db:
            job = await db.get(Job, job_id)
            execution = await db.get(JobExecution, execution_id)
            execution.status = ExecutionStatus.FAILURE
            execution.completed_at = datetime.now(timezone.utc)
            execution.error_message = str(e)

            if job.retry_count < job.max_retries:
                job.retry_count += 1
                job.status = JobStatus.SCHEDULED
                job.execution_time = datetime.now(timezone.utc) + timedelta(seconds=30 * job.retry_count)
                logger.warning("Job %s failed, retrying (%d/%d)", job.id, job.retry_count, job.max_retries)
            else:
                job.status = JobStatus.FAILED
                logger.error("Job %s failed permanently after %d retries", job.id, job.retry_count)
                user = await db.get(User, job.user_id)
                if user and user.email:
                    await send_failure_email(user.email, str(job.id), job.name, str(e))
            
            await db.commit()


async def worker(session_factory: async_sessionmaker, queue: asyncio.Queue) -> None:
    while True:
        job_id, execution_id = await queue.get()
        try:
            await _execute_job(session_factory, job_id, execution_id)
        except Exception:
            logger.exception("Worker error for job %s", job_id)
        finally:
            queue.task_done()
