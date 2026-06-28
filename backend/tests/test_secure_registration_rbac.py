"""SPEC-001 / T1.1 — Secure registration & minimal-privilege RBAC.

Covers the acceptance criteria of issue #153:
- AC1: anonymous signup gets the minimal-privilege role and cannot run
  pipelines, upload RAG documents nor invoke the scraper (403).
- AC2: a non-admin user that tries to change a role gets 403; only ADMIN can.
- AC3: ENABLE_DEV_ROLE_PROMOTION is fail-safe False when unset, and the
  dev/promote-reviewer endpoint answers 403.
"""
import io
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure the backend package is importable.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Dedicated SQLite database for these tests.
TEST_DB_PATH = (ROOT_DIR / "tests" / "test_rbac.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from app.main import app, ensure_local_admin_user  # noqa: E402
from app.shared.database import Base, engine  # noqa: E402


async def _reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def _register(client: AsyncClient, email: str) -> str:
    """Register a user and return its access token."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": "Anon User"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ─── AC1: minimal-privilege role on signup + no privileged actions ─────────────


@pytest.mark.asyncio
async def test_register_assigns_minimal_privilege_role() -> None:
    await _reset_database()
    try:
        async with _client() as client:
            token = await _register(client, "anon@example.com")
            headers = {"Authorization": f"Bearer {token}"}

            me = await client.get("/api/v1/auth/me", headers=headers)
            assert me.status_code == 200
            # Minimal privilege: never REDACTOR/ADMIN on signup.
            assert me.json()["role"] in ("lector", "publico")
            assert me.json()["role"] == "lector"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_fresh_user_cannot_run_pipeline_upload_rag_or_scrape() -> None:
    await _reset_database()
    try:
        async with _client() as client:
            token = await _register(client, "anon2@example.com")
            headers = {"Authorization": f"Bearer {token}"}

            # Pipeline execution (which internally drives the scraper) → 403.
            run = await client.post(
                "/api/v1/agents/00000000-0000-0000-0000-000000000001/run",
                headers=headers,
                json={"flow_sequence": ["investigador"]},
            )
            assert run.status_code == 403, run.text

            # Agent-scoped RAG upload → 403.
            up = await client.post(
                "/api/v1/agents/investigador/rag/upload",
                headers=headers,
                files={"file": ("doc.txt", io.BytesIO(b"hello world"), "text/plain")},
            )
            assert up.status_code == 403, up.text

            # Global RAG library upload → 403.
            lib = await client.post(
                "/api/v1/agents/rag/library/upload",
                headers=headers,
                files={"file": ("doc.txt", io.BytesIO(b"hello world"), "text/plain")},
            )
            assert lib.status_code == 403, lib.text
    finally:
        await engine.dispose()


# ─── AC2: only ADMIN can change roles ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_cannot_change_role() -> None:
    await _reset_database()
    try:
        async with _client() as client:
            token = await _register(client, "wannabe@example.com")
            me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            user_id = me.json()["id"]

            # Self-promotion attempt by a non-admin → 403.
            resp = await client.put(
                f"/api/v1/auth/users/{user_id}/role",
                headers={"Authorization": f"Bearer {token}"},
                json={"role": "admin"},
            )
            assert resp.status_code == 403, resp.text
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_can_change_role() -> None:
    await _reset_database()
    await ensure_local_admin_user()
    try:
        async with _client() as client:
            token = await _register(client, "target@example.com")
            me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
            target_id = me.json()["id"]

            admin_login = await client.post(
                "/api/v1/auth/login",
                json={"email": "admin@admin", "password": os.environ.get("DEV_ADMIN_PASSWORD", "admin123")},
            )
            assert admin_login.status_code == 200, admin_login.text
            admin_token = admin_login.json()["access_token"]

            resp = await client.put(
                f"/api/v1/auth/users/{target_id}/role",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"role": "redactor"},
            )
            assert resp.status_code == 200, resp.text
            assert resp.json()["role"] == "redactor"
    finally:
        await engine.dispose()


# ─── AC3: dev role-promotion fail-safe ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_dev_promote_reviewer_is_forbidden_by_default() -> None:
    await _reset_database()
    try:
        async with _client() as client:
            token = await _register(client, "devpromote@example.com")
            resp = await client.post(
                "/api/v1/auth/dev/promote-reviewer",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 403, resp.text
    finally:
        await engine.dispose()


def test_enable_dev_role_promotion_failsafe_when_unset(monkeypatch) -> None:
    """When the flag is absent from config.yaml and env, it resolves to False."""
    from app.core import config as config_module

    monkeypatch.delenv("ENABLE_DEV_ROLE_PROMOTION", raising=False)
    monkeypatch.delenv("DEFAULT_SIGNUP_ROLE", raising=False)
    monkeypatch.setattr(config_module, "_read_yaml_config", lambda: {})

    rebuilt = config_module._build_settings()
    assert rebuilt.ENABLE_DEV_ROLE_PROMOTION is False
    assert rebuilt.DEFAULT_SIGNUP_ROLE == "lector"
