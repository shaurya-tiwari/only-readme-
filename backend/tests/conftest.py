"""
Test configuration and fixtures.
"""

import os
from uuid import uuid4

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://rideshield:rideshield123@localhost:5433/rideshield_work_test_db"
os.environ["DATABASE_URL_SYNC"] = "postgresql://rideshield:rideshield123@localhost:5433/rideshield_work_test_db"
os.environ["SESSION_SECRET"] = "rideshield-test-secret"
os.environ["SESSION_COOKIE_SECURE"] = "false"
os.environ["ADMIN_PASSWORD"] = "rideshield-test-admin-password"
os.environ["ADMIN_USERNAME"] = "admin"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.core.location_service import location_service
from backend.core.rate_limit import auth_rate_limiter
from backend.database import Base, close_db, engine
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def ensure_db():
    if "test" not in settings.DATABASE_URL.lower():
        raise RuntimeError(f"Refusing to drop non-test database: {settings.DATABASE_URL}")

    await close_db()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    from backend.database import async_session_factory

    async with async_session_factory() as session:
        await location_service.ensure_bootstrap(session, strict_backfill=True)
        await session.commit()
    await auth_rate_limiter.reset()
    yield
    await close_db()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def admin_headers(client):
    response = await client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "rideshield-test-admin-password"},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_cookies(client):
    response = await client.post(
        "/api/auth/admin/login",
        json={"username": "admin", "password": "rideshield-test-admin-password"},
    )
    assert response.status_code == 200
    return dict(client.cookies)


@pytest.fixture
def valid_worker_data():
    phone_suffix = str(uuid4().int)[-10:]
    return {
        "name": "Test Worker",
        "phone": f"+91{phone_suffix}",
        "password": "testworker123",
        "city": "delhi",
        "zone": "south_delhi",
        "platform": "zomato",
        "self_reported_income": 900,
        "working_hours": 9,
        "consent_given": True,
    }


@pytest.fixture
def valid_policy_data():
    return {
        "plan_name": "smart_protect",
    }
