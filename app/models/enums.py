from enum import StrEnum


class JobType(StrEnum):
    SCRIPT = "script"
    API_CALL = "api_call"
    DATA_PROCESS = "data_process"

class ScheduleType(StrEnum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"

class JobStatus(StrEnum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
