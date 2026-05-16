from datetime import datetime, timezone, timedelta


JOB_PAYLOAD = {
    "name": "Test Job",
    "job_type": "script",
    "payload": {"script_path": "/tmp/test.py", "args": [], "env": {}},
    "schedule_type": "one_time",
    "execution_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
}


async def test_submit_job(client, auth_headers):
    response = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["status"] == "scheduled"


async def test_submit_recurring_job(client, auth_headers):
    response = await client.post("/jobs", json={
        "name": "Recurring Job",
        "job_type": "script",
        "payload": {"script_path": "/tmp/recurring.py", "args": [], "env": {}},
        "schedule_type": "recurring",
        "recurrence_pattern": "0 * * * *"
    }, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()["status"] == "scheduled"


async def test_list_jobs(client, auth_headers):
    await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    response = await client.get("/jobs", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


async def test_get_job(client, auth_headers):
    response = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = response.json()["id"]
    response = await client.get(f"/jobs/{job_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == job_id


async def test_get_job_not_found(client, auth_headers):
    response = await client.get("/jobs/00000000-0000-0000-0000-000000000000", headers=auth_headers)
    assert response.status_code == 404


async def test_cancel_job(client, auth_headers):
    response = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = response.json()["id"]
    response = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


async def test_cancel_already_cancelled_job(client, auth_headers):
    created = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = created.json()["id"]
    await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
    response = await client.post(f"/jobs/{job_id}/cancel", headers=auth_headers)
    assert response.status_code == 400


async def test_reschedule_job(client, auth_headers):
    response = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = response.json()["id"]
    new_execution_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    response = await client.put(f"/jobs/{job_id}/reschedule", json={"execution_time": new_execution_time}, headers=auth_headers)
    assert response.status_code == 200


async def test_cannot_access_other_users_jobs(client, auth_headers):
    response = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = response.json()["id"]
    
    await client.post("/auth/register", json={"username": "otheruser", "email": "otheruser@example.com", "password": "password"})
    login = await client.post("/auth/login", json={"username": "otheruser", "password": "password"})
    other_auth_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.get(f"/jobs/{job_id}", headers=other_auth_headers)
    assert response.status_code == 404


async def test_get_job_executions_empty(client, auth_headers):
    response = await client.post("/jobs", json=JOB_PAYLOAD, headers=auth_headers)
    job_id = response.json()["id"]
    response = await client.get(f"/jobs/{job_id}/executions", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []
