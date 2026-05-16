import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.monitor import router as monitor_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, verify_db_connection
from app.scheduler.scheduler import poll
from app.scheduler.worker import worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_db_connection()

    queue: asyncio.Queue = asyncio.Queue()

    worker_tasks = [
        asyncio.create_task(worker(AsyncSessionLocal, queue))
        for _ in range(3)
    ]
    scheduler_task = asyncio.create_task(
        poll(AsyncSessionLocal, queue, settings.SCHEDULER_POLL_INTERVAL)
    )

    yield

    scheduler_task.cancel()
    for t in worker_tasks:
        t.cancel()


app = FastAPI(title="Chronos", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(monitor_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
