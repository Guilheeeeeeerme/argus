"""Public sign-up (register) endpoint tests."""

from __future__ import annotations

import os
import uuid

import bcrypt
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

os.environ.setdefault("AUTH0_USE_MOCK", "true")
os.environ.setdefault("AUTH0_DOMAIN", "dev.argus.local")

from argus.apps.http import create_admin_app
from argus.config import get_settings
from argus.domain.enums import UserRole
from argus.domain.models import CompanyUser
from argus.services.database import company_session, dispose_engine
from argus.services.redis import close_redis
from argus.services.sessions import get_session

get_settings.cache_clear()

_CREATED_EMAILS: list[str] = []


@pytest_asyncio.fixture(autouse=True)
async def _cleanup():
    yield
    for email in _CREATED_EMAILS:
        async with company_session(None, UserRole.ROOT.value) as session:
            await session.execute(delete(CompanyUser).where(CompanyUser.email == email))
    _CREATED_EMAILS.clear()
    await close_redis()
    await dispose_engine()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=create_admin_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _unique_email() -> str:
    email = f"{uuid.uuid4()}@example.com"
    _CREATED_EMAILS.append(email)
    return email


@pytest.mark.asyncio
async def test_register_creates_user_and_session(client: AsyncClient) -> None:
    email = _unique_email()
    response = await client.post(
        "/v1/auth/register",
        json={"email": email, "password": "S3curePass!"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token"].startswith("sess_")
    assert body["user"]["email"] == email
    assert body["user"]["role"] == "operator"
    assert body["user"]["companyId"] is None
    assert body["activeCompany"] is None
    assert body["activeLocation"] is None

    session_data = await get_session(body["token"])
    assert session_data is not None
    assert session_data.email == email
    assert session_data.role == "operator"
    assert session_data.company_id is None

    async with company_session(None, UserRole.ROOT.value) as session:
        user = await session.scalar(select(CompanyUser).where(CompanyUser.email == email))
    assert user is not None
    assert user.password_hash is not None
    assert bcrypt.checkpw("S3curePass!".encode(), user.password_hash.encode())


@pytest.mark.asyncio
async def test_register_duplicate_email_conflict(client: AsyncClient) -> None:
    email = _unique_email()
    payload = {"email": email, "password": "S3curePass!"}
    first = await client.post("/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/v1/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_register_short_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/register",
        json={"email": "short-pw@example.com", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_over_limit_password_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/v1/auth/register",
        json={"email": "long-pw@example.com", "password": "a" * 73},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_normalizes_email(client: AsyncClient) -> None:
    email = _unique_email()
    first = await client.post(
        "/v1/auth/register",
        json={"email": email.upper(), "password": "S3curePass!"},
    )
    assert first.status_code == 201
    second = await client.post("/v1/auth/register", json={"email": email, "password": "S3curePass!"})
    assert second.status_code == 409
    assert first.json()["user"]["email"] == email
