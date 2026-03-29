"""
Test configuration and fixtures.
"""

import os

os.environ["ENV"] = "test"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from backend.config import settings
from backend.database import Base, close_db, engine
from backend.main import app


@pytest_asyncio.fixture(autouse=True)
async def ensure_db():
    if "test" not in settings.DATABASE_URL.lower():
        raise RuntimeError(f"Refusing to drop non-test database: {settings.DATABASE_URL}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
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
        json={"username": "admin", "password": "rideshield-admin"},
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def valid_worker_data():
    return {
        "name": "Test Worker",
        "phone": "+919999999999",
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
