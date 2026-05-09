from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.database import verify_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    await verify_db_connection()
    yield

app = FastAPI(title="Chronos", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}