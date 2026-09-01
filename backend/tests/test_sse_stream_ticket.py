"""SSE stream ticket auth tests (task T1.4, #156).

Verifies that the agent-run SSE stream no longer accepts a JWT in the query
string and is instead authenticated with a short-lived, single-use ticket.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_sse_ticket.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from app.core import stream_auth  # noqa: E402
from app.core.stream_auth import consume_ticket, issue_ticket, reset_stream_tickets  # noqa: E402
from app.main import app  # noqa: E402
from app.models import ArticleModel, UserModel  # noqa: E402
from app.core.database import Base, engine  # noqa: E402


@pytest_asyncio.fixture(autouse=True)
async def _reset_tickets():
    """El almacén de tickets vive ahora en el bus (SPEC-018/T4.3), así que
    vaciarlo es una operación async."""
    await reset_stream_tickets()
    yield
    await reset_stream_tickets()


# ── Unit: ticket store ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_issue_and_consume_roundtrip():
    ticket = await issue_ticket("user-1", "article-1")
    assert await consume_ticket(ticket, "article-1") == "user-1"


@pytest.mark.asyncio
async def test_ticket_is_single_use():
    ticket = await issue_ticket("user-1", "article-1")
    assert await consume_ticket(ticket, "article-1") == "user-1"
    assert await consume_ticket(ticket, "article-1") is None


@pytest.mark.asyncio
async def test_ticket_article_mismatch_is_rejected_and_consumed():
    ticket = await issue_ticket("user-1", "article-1")
    assert await consume_ticket(ticket, "article-2") is None
    # even the correct article can no longer use it (single-use on any attempt)
    assert await consume_ticket(ticket, "article-1") is None


@pytest.mark.asyncio
async def test_expired_ticket_is_rejected(monkeypatch):
    """El reloj que cuenta vive ahora en el bus, no en `stream_auth`."""
    from app.platform import bus as bus_module

    ticket = await issue_ticket("user-1", "article-1", ttl_seconds=30)
    ahora = bus_module.time.monotonic()
    monkeypatch.setattr(bus_module.time, "monotonic", lambda: ahora + 61)
    assert await consume_ticket(ticket, "article-1") is None


@pytest.mark.asyncio
async def test_empty_ticket_is_rejected():
    assert await consume_ticket("", "article-1") is None
    assert await consume_ticket(None, "article-1") is None


# ── Integration: endpoints ──────────────────────────────────────────────────────

async def _reset_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _cleanup_db() -> None:
    if TEST_DB_PATH.exists():
        try:
            TEST_DB_PATH.unlink()
        except Exception:
            pass


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


async def _register(client: AsyncClient, email: str) -> tuple[str, str]:
    """Register a user; return (bearer_token, user_id)."""
    res = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "StrongPass123", "full_name": "T"},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    async with AsyncSession(engine) as s:
        user = (await s.execute(select(UserModel).where(UserModel.email == email))).scalars().first()
        return token, str(user.id)


async def _create_article(author_id: str) -> str:
    # expire_on_commit=False keeps art.id readable after commit without an async
    # refresh (which would raise MissingGreenlet in this sync access).
    async with AsyncSession(engine, expire_on_commit=False) as s:
        art = ArticleModel(title="Test article", author_id=uuid.UUID(author_id))
        s.add(art)
        await s.commit()
        return str(art.id)


@pytest.mark.asyncio
async def test_stream_rejects_without_valid_ticket():
    await _reset_db()
    try:
        article_id = "00000000-0000-0000-0000-000000000001"
        async with _client() as client:
            # no ticket
            assert (await client.get(f"/api/v1/agents/{article_id}/stream")).status_code == 401
            # bogus ticket
            assert (await client.get(f"/api/v1/agents/{article_id}/stream?ticket=nope")).status_code == 401
            # legacy ?token=<JWT> is no longer accepted
            assert (await client.get(f"/api/v1/agents/{article_id}/stream?token=whatever")).status_code == 401
    finally:
        await engine.dispose()
        _cleanup_db()


@pytest.mark.asyncio
async def test_stream_ticket_requires_authentication():
    await _reset_db()
    try:
        article_id = "00000000-0000-0000-0000-000000000001"
        async with _client() as client:
            res = await client.post(f"/api/v1/agents/{article_id}/stream-ticket")
        assert res.status_code in (401, 403)
    finally:
        await engine.dispose()
        _cleanup_db()


@pytest.mark.asyncio
async def test_owner_gets_valid_single_use_ticket():
    await _reset_db()
    try:
        async with _client() as client:
            token, user_id = await _register(client, "owner@example.com")
            article_id = await _create_article(user_id)

            res = await client.post(
                f"/api/v1/agents/{article_id}/stream-ticket",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 200, res.text
            ticket = res.json()["ticket"]
            assert ticket

            # The issued ticket authenticates this user for this article, once.
            assert await consume_ticket(ticket, article_id) == user_id
            assert await consume_ticket(ticket, article_id) is None
    finally:
        await engine.dispose()
        _cleanup_db()


@pytest.mark.asyncio
async def test_non_owner_cannot_get_ticket():
    await _reset_db()
    try:
        async with _client() as client:
            _, owner_id = await _register(client, "owner2@example.com")
            article_id = await _create_article(owner_id)
            intruder_token, _ = await _register(client, "intruder@example.com")

            res = await client.post(
                f"/api/v1/agents/{article_id}/stream-ticket",
                headers={"Authorization": f"Bearer {intruder_token}"},
            )
        assert res.status_code == 403
    finally:
        await engine.dispose()
        _cleanup_db()
