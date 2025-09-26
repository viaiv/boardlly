import base64
import os

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import deps
from app.db.base import Base
from main import app

os.environ.setdefault("TACTYO_SESSION_SECRET", "test-secret-value-123456")
os.environ.setdefault(
    "TACTYO_ENCRYPTION_KEY",
    base64.b64encode(b"0123456789abcdef0123456789abcdef").decode(),
)


def create_sqlite_engine():
    return create_async_engine("sqlite+aiosqlite:///:memory:", future=True)


@pytest.fixture
async def client_session():
    engine = create_sqlite_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    TestingSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session

    app.dependency_overrides[deps.get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as test_client:
        yield test_client, TestingSessionLocal

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def client(client_session):
    test_client, _ = client_session
    return test_client


@pytest.fixture
def session_factory(client_session):
    _, session_factory = client_session
    return session_factory
