from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import verify_db_connection
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_db_connection()
    yield

app = FastAPI(title="Chronos", version="0.1.0", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(jobs_router)

@app.get("/health")
async def health():
    return {"status": "ok"}
