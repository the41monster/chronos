import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator

from app.models.enums import JobStatus, JobType, ScheduleType, ExecutionStatus


class JobSubmitRequest(BaseModel):
    name: str
    description: str | None = None
    job_type: JobType
    payload: dict[str, Any]
    schedule_type: ScheduleType
    execution_time: datetime | None = None
    recurrence_pattern: str | None = None

    @model_validator(mode="after")
    def validate_schedule_fields(self) -> "JobSubmitRequest":
        if self.schedule_type == ScheduleType.ONE_TIME and not self.execution_time:
            raise ValueError("execution_time is required for one_time jobs")
        if self.schedule_type == ScheduleType.RECURRING and not self.recurrence_pattern:
            raise ValueError("recurrence_pattern is required for recurring jobs")
        return self


class JobSubmitResponse(BaseModel):
    id: uuid.UUID
    status: JobStatus

    model_config = {"from_attributes": True}


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str | None
    job_type: JobType
    payload: dict[str, Any]
    schedule_type: ScheduleType
    execution_time: datetime | None
    recurrence_pattern: str | None
    status: JobStatus
    max_retries: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RescheduleRequest(BaseModel):
    execution_time: datetime | None = None
    recurrence_pattern: str | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "RescheduleRequest":
        if not self.execution_time and not self.recurrence_pattern:
            raise ValueError("At least one of execution_time or recurrence_pattern must be provided")
        return self


class JobExecutionResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    status: ExecutionStatus
    started_at: datetime
    completed_at: datetime | None
    retry_count: int
    log_output: str | None
    error_message: str | None

    model_config = {"from_attributes": True}
