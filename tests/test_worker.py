import uuid
import pytest
from datetime import datetime, timezone

from app.models.enums import ExecutionStatus, JobStatus, JobType, ScheduleType
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.models.user import User
from app.scheduler.worker import _execute_job
from tests.conftest import TestSessionLocal


@pytest.fixture
def script_path(tmp_path):
    script_file = tmp_path / "test_script.py"
    script_file.write_text("print('Hello from Chronos test script')")
    return str(script_file)


async def _create_job_and_execution(job_type=JobType.SCRIPT, payload=None, schedule_type=ScheduleType.ONE_TIME):
    async with TestSessionLocal() as db:
        user = User(
            username=f"worker_test_{uuid.uuid4().hex[:8]}",
            email=f"worker_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="password",
        )
        db.add(user)
        await db.flush()
        job = Job(
            user_id=user.id,
            name="test job",
            job_type=job_type,
            payload=payload or {},
            schedule_type=schedule_type,
            execution_time=datetime.now(timezone.utc),
            status=JobStatus.RUNNING,
        )
        db.add(job)
        await db.flush()
        execution = JobExecution(
            job_id=job.id,
            started_at=datetime.now(timezone.utc),
            status=ExecutionStatus.RUNNING,
        )
        db.add(execution)
        await db.commit()
        return job.id, execution.id


async def test_script_job_success(script_path):
    job_id, execution_id = await _create_job_and_execution(payload={"script_path": script_path, "args": [], "env": {}})
    await _execute_job(TestSessionLocal, job_id, execution_id)

    async with TestSessionLocal() as db:
        execution = await db.get(JobExecution, execution_id)
        job = await db.get(Job, job_id)
        assert execution is not None
        assert job is not None
        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.log_output is not None
        assert job.status == JobStatus.COMPLETED


async def test_script_job_failure():
    job_id, execution_id = await _create_job_and_execution(
        payload={"script_path": "d:/nonexistent/script.py", "args": [], "env": {}}
    )
    await _execute_job(TestSessionLocal, job_id, execution_id)

    async with TestSessionLocal() as db:
        execution = await db.get(JobExecution, execution_id)
        job = await db.get(Job, job_id)
        assert execution is not None
        assert job is not None
        assert execution.status == ExecutionStatus.FAILURE
        assert execution.error_message is not None
        assert job.status == JobStatus.SCHEDULED
        assert job.retry_count == 1


async def test_max_retries_exhausted():
    job_id, execution_id = await _create_job_and_execution(
        payload={"script_path": "d:/nonexistent/script.py", "args": [], "env": {}}
    )
    async with TestSessionLocal() as db:
        job = await db.get(Job, job_id)
        assert job is not None
        job.retry_count = job.max_retries
        await db.commit()

    await _execute_job(TestSessionLocal, job_id, execution_id)

    async with TestSessionLocal() as db:
        job = await db.get(Job, job_id)
        assert job is not None
        assert job.status == JobStatus.FAILED


async def test_api_call_job_success():
    job_id, execution_id = await _create_job_and_execution(
        job_type=JobType.API_CALL,
        payload={"url": "https://httpbin.org/get", "method": "GET", "headers": {}, "body": None},
    )
    await _execute_job(TestSessionLocal, job_id, execution_id)

    async with TestSessionLocal() as db:
        execution = await db.get(JobExecution, execution_id)
        assert execution is not None
        assert execution.status == ExecutionStatus.SUCCESS
        assert execution.log_output is not None
        assert "200" in execution.log_output


async def test_data_process_job():
    job_id, execution_id = await _create_job_and_execution(
        job_type=JobType.DATA_PROCESS,
        payload={},
    )
    await _execute_job(TestSessionLocal, job_id, execution_id)

    async with TestSessionLocal() as db:
        execution = await db.get(JobExecution, execution_id)
        assert execution is not None
        assert execution.status == ExecutionStatus.SUCCESS
