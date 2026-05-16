import uuid
from datetime import datetime

from pydantic import BaseModel


class JobStatusCounts(BaseModel):
    pending: int
    scheduled: int
    running: int
    completed: int
    failed: int
    cancelled: int


class FailedJobSummary(BaseModel):
    id: uuid.UUID
    name: str
    user_id: uuid.UUID
    retry_count: int
    max_retries: int
    updated_at: datetime
    last_error: str | None

    model_config = {"from_attributes": True}
