from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.job import Job
from app.models.user import User
from app.schemas.job import JobSubmitRequest, JobSubmitResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobSubmitResponse, status_code=201)
async def submit_job(
    payload: JobSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    job = Job(
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
        job_type=payload.job_type,
        payload=payload.payload,
        schedule_type=payload.schedule_type,
        execution_time=payload.execution_time,
        recurrence_pattern=payload.recurrence_pattern
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job
