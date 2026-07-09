import os
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient

# Asegurar que la carpeta backend esté en sys.path para importar la app.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Usar una base de datos SQLite dedicada para el test.
TEST_DB_PATH = (ROOT_DIR / "tests" / "test_auth.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from app.main import app  # noqa: E402, isort:skip
from app.core.database import Base, engine  # noqa: E402, isort:skip


async def _create_test_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest.mark.asyncio
async def test_register_login_and_get_current_user() -> None:
    await _create_test_database()
    try:
        register_payload = {
            "email": "test-user@example.com",
            "password": "StrongPass123",
            "full_name": "Test User",
        }

        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post("/api/v1/auth/register", json=register_payload)

            assert response.status_code == 200
            response_data = response.json()
            assert "access_token" in response_data
            assert response_data.get("token_type") == "bearer"

            access_token = response_data["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            current_user_response = await client.get("/api/v1/auth/me", headers=headers)
            assert current_user_response.status_code == 200
            current_user = current_user_response.json()
            assert current_user["email"] == register_payload["email"]
            assert current_user["full_name"] == register_payload["full_name"]

            login_payload = {
                "email": register_payload["email"],
                "password": register_payload["password"],
            }
            login_response = await client.post("/api/v1/auth/login", json=login_payload)
            assert login_response.status_code == 200
            login_data = login_response.json()
            assert "access_token" in login_data
            assert login_data.get("token_type") == "bearer"

            second_access_token = login_data["access_token"]
            assert second_access_token != access_token

            current_user_response_2 = await client.get(
                "/api/v1/auth/me", headers={"Authorization": f"Bearer {second_access_token}"}
            )
            assert current_user_response_2.status_code == 200
            assert current_user_response_2.json()["email"] == register_payload["email"]
    finally:
        await engine.dispose()
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass


@pytest.mark.asyncio
async def test_seeded_public_user_login() -> None:
    await _create_test_database()
    from app.main import ensure_dev_users
    await ensure_dev_users()
    try:
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            login_payload = {
                "email": "publico@example.com",
                "password": "publico123",
            }
            response = await client.post("/api/v1/auth/login", json=login_payload)
            assert response.status_code == 200
            response_data = response.json()
            assert "access_token" in response_data
            
            access_token = response_data["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            me_res = await client.get("/api/v1/auth/me", headers=headers)
            assert me_res.status_code == 200
            me_data = me_res.json()
            assert me_data["email"] == "publico@example.com"
            assert me_data["role"] == "publico"
    finally:
        await engine.dispose()
        if TEST_DB_PATH.exists():
            try:
                TEST_DB_PATH.unlink()
            except Exception:
                pass
