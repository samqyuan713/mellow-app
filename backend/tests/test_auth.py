"""
Mellow — Auth Tests
pytest test suite for authentication endpoints.
"""

import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.asyncio
async def test_register_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/register", json={
            "email": "test@mellow.app",
            "password": "Test1234",
            "first_name": "Alex"
        })
    assert res.status_code == 201
    data = res.json()
    assert "tokens" in data
    assert data["user"]["email"] == "test@mellow.app"


@pytest.mark.asyncio
async def test_register_duplicate_email():
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {"email": "dup@mellow.app", "password": "Test1234", "first_name": "Alex"}
        await client.post("/api/v1/auth/register", json=payload)
        res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/register", json={
            "email": "weak@mellow.app",
            "password": "weak",
            "first_name": "Alex"
        })
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.post("/api/v1/auth/login", json={
            "email": "nobody@mellow.app",
            "password": "WrongPass1"
        })
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        res = await client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
