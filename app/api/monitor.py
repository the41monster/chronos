from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import verify_monitor_key
from app.models.enums import JobStatus
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.schemas.monitor import FailedJobSummary, JobStatusCounts

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/health", response_model=JobStatusCounts, dependencies=[Depends(verify_monitor_key)])
async def health_monitor(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            Job.status, func.count().label("total")
        ).group_by(Job.status)
    )
    rows = result.all()
    counts = {row.status: row.total for row in rows}
    return JobStatusCounts(
        pending=counts.get(JobStatus.PENDING, 0),
        scheduled=counts.get(JobStatus.SCHEDULED, 0),
        running=counts.get(JobStatus.RUNNING, 0),
        completed=counts.get(JobStatus.COMPLETED, 0),
        failed=counts.get(JobStatus.FAILED, 0),
        cancelled=counts.get(JobStatus.CANCELLED, 0)
    )


@router.get("/failures", response_model=list[FailedJobSummary], dependencies=[Depends(verify_monitor_key)])
async def monitor_failures(db: AsyncSession = Depends(get_db)):
    latest_error = (
        select(
            JobExecution.job_id,
            func.max(JobExecution.started_at).label("latest_started_at")
        )
        .group_by(JobExecution.job_id)
        .subquery()
    )

    result = await db.execute(
        select(
            Job.id,
            Job.name,
            Job.user_id,
            Job.retry_count,
            Job.max_retries,
            Job.updated_at,
            JobExecution.error_message.label("last_error")
        )
        .join(latest_error, latest_error.c.job_id == Job.id)
        .join(
            JobExecution,
            (JobExecution.job_id == Job.id) &
            (JobExecution.started_at == latest_error.c.latest_started_at)
        )
        .where(Job.status == JobStatus.FAILED)
        .order_by(Job.updated_at.desc())
    )
    return result.mappings().all()
