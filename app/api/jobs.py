import uuid
from datetime import datetime, timezone
from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.enums import JobStatus, ScheduleType
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobResponse, JobSubmitRequest, JobSubmitResponse, RescheduleRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobSubmitResponse, status_code=status.HTTP_201_CREATED)
async def submit_job(
    payload: JobSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    execution_time = payload.execution_time
    if payload.schedule_type == ScheduleType.RECURRING and not execution_time and payload.recurrence_pattern:
        cron = croniter(payload.recurrence_pattern, datetime.now(timezone.utc))
        execution_time = cron.get_next(datetime)
    
    job = Job(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        job_type=payload.job_type,
        payload=payload.payload,
        schedule_type=payload.schedule_type,
        execution_time=execution_time,
        recurrence_pattern=payload.recurrence_pattern
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("", response_model=list[JobResponse])
async def list_jobs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.user_id == current_user.id))
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in (JobStatus.PENDING, JobStatus.SCHEDULED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending or scheduled jobs can be cancelled")
    job.status = JobStatus.CANCELLED
    await db.commit()
    await db.refresh(job)
    return job


@router.put("/{job_id}/reschedule", response_model=JobResponse)
async def reschedule_job(
    job_id: uuid.UUID,
    payload: RescheduleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    job = await db.get(Job, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in (JobStatus.PENDING, JobStatus.SCHEDULED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending or scheduled jobs can be rescheduled")
    if payload.execution_time:
        job.execution_time = payload.execution_time
    if payload.recurrence_pattern:
        job.recurrence_pattern = payload.recurrence_pattern
    job.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job
