import uuid
from datetime import datetime, timezone

import pytest

from app.core.config import settings
from app.models.enums import ExecutionStatus, JobStatus, JobType, ScheduleType
from app.models.job import Job
from app.models.job_execution import JobExecution
from app.models.user import User
from tests.conftest import TestSessionLocal


@pytest.fixture
def monitor_headers():
    return {"X-Monitor-Key": settings.MONITOR_API_KEY}


async def test_health_no_jobs(client, monitor_headers):
    response = await client.get("/monitor/health", headers=monitor_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["scheduled"] == 0
    assert data["failed"] == 0
    assert data["completed"] == 0


async def test_health_counts(client, auth_headers, monitor_headers):
    await client.post("/jobs", json={
        "name": "job1",
        "job_type": "script",
        "payload": {"script_path": "/tmp/test.py"},
        "schedule_type": "one_time",
        "execution_time": "2026-12-01T00:00:00Z",
    }, headers=auth_headers)
    response = await client.get("/monitor/health", headers=monitor_headers)
    assert response.status_code == 200
    assert response.json()["scheduled"] == 1


async def test_health_missing_key(client):
    response = await client.get("/monitor/health")
    assert response.status_code == 401


async def test_health_invalid_key(client):
    response = await client.get("/monitor/health", headers={"X-Monitor-Key": "wrong"})
    assert response.status_code == 401


async def test_failures_empty(client, monitor_headers):
    response = await client.get("/monitor/failures", headers=monitor_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_failures_returns_failed_jobs(client, monitor_headers):
    async with TestSessionLocal() as db:
        user = User(
            username=f"monitor_test_{uuid.uuid4().hex[:8]}",
            email=f"monitor_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="password",
        )
        db.add(user)
        await db.flush()
        job = Job(
            user_id=user.id,
            name="failed job",
            job_type=JobType.SCRIPT,
            payload={},
            schedule_type=ScheduleType.ONE_TIME,
            execution_time=datetime.now(timezone.utc),
            status=JobStatus.FAILED,
            retry_count=3,
        )
        db.add(job)
        await db.flush()
        execution = JobExecution(
            job_id=job.id,
            started_at=datetime.now(timezone.utc),
            status=ExecutionStatus.FAILURE,
            error_message="something went wrong",
        )
        db.add(execution)
        await db.commit()

    response = await client.get("/monitor/failures", headers=monitor_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "failed job"
    assert data[0]["last_error"] == "something went wrong"


async def test_failures_missing_key(client):
    response = await client.get("/monitor/failures")
    assert response.status_code == 401
