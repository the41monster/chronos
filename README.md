# Chronos

A distributed job scheduling system built with FastAPI and PostgreSQL. Supports one-time and recurring jobs, automatic retries, and real-time execution monitoring.

## Architecture

Chronos runs as a single process — the FastAPI app, scheduler, and worker pool all share the same event loop.

- **Scheduler** — polls the database every N seconds for due jobs and enqueues them
- **Worker pool** — 3 concurrent workers consume from the queue and execute jobs
- **Job types** — `script` (subprocess), `api_call` (HTTP request), `data_process` (placeholder)
- **Retry logic** — failed jobs are retried up to 3 times with linear backoff (30s × retry count); permanent failures trigger an email notification if SMTP is configured

## Prerequisites

- Docker

## Quick Start (Docker)

**1. Clone and configure**

```bash
git clone https://github.com/the41monster/chronos.git
cd chronos
cp .env.example .env
```

Edit `.env` with your values — see [Environment Variables](#environment-variables) below.

**2. Start everything**

```bash
docker compose up --build
```

This starts the database, runs migrations, and launches the API and frontend.

| Service | URL |
|---|---|
| Frontend | http://localhost:8080 |
| API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

## Running Script Jobs

Script jobs execute Python files inside the API container. Place your scripts in the `scripts/` folder at the project root — it is mounted at `/app/scripts` inside the container.

```
scripts/
  hello.py   →   /app/scripts/hello.py  (use this path when submitting the job)
```

## Local Setup (without Docker)

**1. Install dependencies**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
```

**3. Start PostgreSQL and run migrations**

```bash
docker compose up -d db
alembic upgrade head
```

**4. Start the server**

```bash
python run.py
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | Async PostgreSQL URL (`postgresql+asyncpg://...`) |
| `POSTGRES_USER` | Yes | — | PostgreSQL user (used by Docker Compose) |
| `POSTGRES_PASSWORD` | Yes | — | PostgreSQL password (used by Docker Compose) |
| `POSTGRES_DB` | Yes | — | PostgreSQL database name (used by Docker Compose) |
| `SECRET_KEY` | Yes | — | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT token lifetime |
| `MONITOR_API_KEY` | No | `""` | Static key for monitoring endpoints (leave empty to disable) |
| `SCHEDULER_POLL_INTERVAL` | No | `10` | Seconds between scheduler polls |
| `SMTP_HOST` | No | `smtp.gmail.com` | SMTP host for failure emails |
| `SMTP_PORT` | No | `587` | SMTP port |
| `SMTP_USERNAME` | No | `""` | SMTP username |
| `SMTP_PASSWORD` | No | `""` | SMTP password |
| `SMTP_FROM` | No | `""` | Sender address for failure emails |

## API Reference

All job endpoints require a Bearer token from `/auth/login`.

### Auth

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Register a new user |
| `POST` | `/auth/login` | Log in, returns JWT |
| `GET` | `/auth/me` | Get current user |

**Register**
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "email": "alice@example.com", "password": "secret"}'
```

**Login**
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "secret"}'
# Returns: {"access_token": "...", "token_type": "bearer"}
```

### Jobs

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/jobs` | Submit a job |
| `GET` | `/jobs` | List your jobs |
| `GET` | `/jobs/{id}` | Get a job |
| `POST` | `/jobs/{id}/cancel` | Cancel a pending or scheduled job |
| `PUT` | `/jobs/{id}/reschedule` | Reschedule a job |
| `GET` | `/jobs/{id}/executions` | List execution history |

**Submit a one-time script job**
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Script",
    "job_type": "script",
    "payload": {"script_path": "/path/to/script.py", "args": [], "env": {}},
    "schedule_type": "one_time",
    "execution_time": "2026-06-01T09:00:00Z"
  }'
```

**Submit a recurring API call job**
```bash
curl -X POST http://localhost:8000/jobs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hourly ping",
    "job_type": "api_call",
    "payload": {"url": "https://example.com/ping", "method": "GET", "headers": {}, "body": null},
    "schedule_type": "recurring",
    "recurrence_pattern": "0 * * * *"
  }'
```

### Monitoring

Monitoring endpoints require the `X-Monitor-Key` header matching `MONITOR_API_KEY`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/monitor/health` | Job counts by status |
| `GET` | `/monitor/failures` | All permanently failed jobs with last error |

```bash
curl http://localhost:8000/monitor/health \
  -H "X-Monitor-Key: <your-monitor-key>"
```

### Health

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## Running Tests

Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Create the test database (one-time):

```bash
docker exec -it <postgres-container> psql -U postgres -c "CREATE DATABASE chronos_test;"
```

Run the test suite:

```bash
pytest
```

With coverage:

```bash
pytest --cov=app --cov-report=term-missing
```
