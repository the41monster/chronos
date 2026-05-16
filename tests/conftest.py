import asyncio

import pytest
import pytest_asyncio
from contextlib import asynccontextmanager
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = settings.DATABASE_URL.replace("/chronos", "/chronos_test")

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

@asynccontextmanager
async def _test_lifespan(app):
    yield

app.router.lifespan_context = _test_lifespan


def pytest_configure(config):
    async def _setup():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_setup())


def pytest_unconfigure(config):
    async def _teardown():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    asyncio.run(_teardown())


@pytest_asyncio.fixture(autouse=True)
async def truncate_tables():
    yield
    async with test_engine.connect() as conn:
        await conn.execute(text("TRUNCATE users, jobs, job_executions CASCADE"))
        await conn.commit()


@pytest.fixture
def override_get_db():
    async def _get_db():
        async with TestSessionLocal() as db:
            yield db
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(override_get_db):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/auth/register", json={
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpassword"
    })
    response = await client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpassword"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
