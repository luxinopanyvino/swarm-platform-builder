"""T1.2 / issue #154 — Rate limiting + account lockout on login/register.

Covers the brute-force / credential-stuffing protections added to the auth
endpoints:
- AC1: per-IP rate limiting returns 429 once the sliding window is exceeded
  (verified on both /register and /login).
- AC2: an account is locked (423) after N consecutive failed logins, and stays
  locked even when the correct password is then supplied.
- AC3: a successful login resets the failed-attempt counter.

The pure throttling primitives are also unit-tested without the HTTP layer.
"""
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# Dedicated SQLite database for these tests.
TEST_DB_PATH = (ROOT_DIR / "tests" / "test_ratelimit.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from app.core import config as config_module  # noqa: E402
from app.core.rate_limit import (  # noqa: E402
    AccountLockoutTracker,
    SlidingWindowCounter,
)
from app.main import app  # noqa: E402
from app.core.database import Base, engine  # noqa: E402


async def _reset_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver")


# ─── Unit tests: throttling primitives ─────────────────────────────────────────


def test_sliding_window_blocks_after_max_attempts() -> None:
    limiter = SlidingWindowCounter()
    now = 1000.0
    # First 3 attempts allowed within the window.
    for _ in range(3):
        assert limiter.check_and_record("ip", max_attempts=3, window_seconds=60, now=now) is None
    # 4th attempt blocked, with a positive retry-after.
    retry = limiter.check_and_record("ip", max_attempts=3, window_seconds=60, now=now)
    assert retry is not None and retry > 0
    # After the window slides past, attempts are allowed again.
    assert limiter.check_and_record("ip", max_attempts=3, window_seconds=60, now=now + 61) is None


def test_sliding_window_disabled_when_max_is_zero() -> None:
    limiter = SlidingWindowCounter()
    for _ in range(100):
        assert limiter.check_and_record("ip", max_attempts=0, window_seconds=60) is None


def test_account_lockout_triggers_and_expires() -> None:
    tracker = AccountLockoutTracker()
    now = 500.0
    # Two failures below the threshold do not lock.
    assert tracker.record_failure("a@b.com", max_failed=3, lockout_seconds=900, now=now) is False
    assert tracker.record_failure("a@b.com", max_failed=3, lockout_seconds=900, now=now) is False
    # Third failure locks the account.
    assert tracker.record_failure("a@b.com", max_failed=3, lockout_seconds=900, now=now) is True
    assert tracker.locked_for("a@b.com", now=now) is not None
    # Lock expires after the configured duration.
    assert tracker.locked_for("a@b.com", now=now + 901) is None


def test_account_lockout_reset_clears_state() -> None:
    tracker = AccountLockoutTracker()
    tracker.record_failure("a@b.com", max_failed=1, lockout_seconds=900, now=0.0)
    assert tracker.locked_for("a@b.com", now=0.0) is not None
    tracker.reset("a@b.com")
    assert tracker.locked_for("a@b.com", now=0.0) is None


# ─── AC1: per-IP rate limiting on the HTTP endpoints ───────────────────────────


@pytest.mark.asyncio
async def test_register_is_rate_limited_per_ip(monkeypatch) -> None:
    await _reset_database()
    monkeypatch.setattr(config_module.settings, "AUTH_RATELIMIT_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(config_module.settings, "AUTH_RATELIMIT_WINDOW_SECONDS", 60)
    try:
        async with _client() as client:
            payload = lambda i: {  # noqa: E731
                "email": f"reg{i}@example.com",
                "password": "StrongPass123",
                "full_name": "User",
            }
            # First 3 registrations allowed.
            for i in range(3):
                resp = await client.post("/api/v1/auth/register", json=payload(i))
                assert resp.status_code == 200, resp.text
            # 4th from the same IP is throttled.
            blocked = await client.post("/api/v1/auth/register", json=payload(99))
            assert blocked.status_code == 429, blocked.text
            assert "Retry-After" in blocked.headers
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_login_is_rate_limited_per_ip(monkeypatch) -> None:
    await _reset_database()
    monkeypatch.setattr(config_module.settings, "AUTH_RATELIMIT_MAX_ATTEMPTS", 4)
    monkeypatch.setattr(config_module.settings, "AUTH_RATELIMIT_WINDOW_SECONDS", 60)
    # Disable lockout so we isolate the rate-limit behaviour.
    monkeypatch.setattr(config_module.settings, "AUTH_LOCKOUT_MAX_FAILED", 0)
    try:
        async with _client() as client:
            body = {"email": "nobody@example.com", "password": "wrong"}
            statuses = []
            for _ in range(6):
                resp = await client.post("/api/v1/auth/login", json=body)
                statuses.append(resp.status_code)
            # The first 4 attempts reach the credential check (401); the rest are
            # rejected by the rate limiter (429).
            assert statuses[:4] == [401, 401, 401, 401]
            assert 429 in statuses[4:]
    finally:
        await engine.dispose()


# ─── AC2 + AC3: account lockout on login ───────────────────────────────────────


@pytest.mark.asyncio
async def test_account_locks_after_consecutive_failures(monkeypatch) -> None:
    await _reset_database()
    # Generous IP limit so the lockout (not the rate limiter) is what triggers.
    monkeypatch.setattr(config_module.settings, "AUTH_RATELIMIT_MAX_ATTEMPTS", 100)
    monkeypatch.setattr(config_module.settings, "AUTH_LOCKOUT_MAX_FAILED", 3)
    monkeypatch.setattr(config_module.settings, "AUTH_LOCKOUT_SECONDS", 900)
    try:
        async with _client() as client:
            reg = await client.post(
                "/api/v1/auth/register",
                json={"email": "victim@example.com", "password": "CorrectHorse1", "full_name": "V"},
            )
            assert reg.status_code == 200, reg.text

            wrong = {"email": "victim@example.com", "password": "bad-guess"}
            # Three wrong attempts: the third trips the lockout.
            for _ in range(3):
                resp = await client.post("/api/v1/auth/login", json=wrong)
                assert resp.status_code == 401, resp.text

            # Account is now locked: even the correct password is refused with 423.
            correct = {"email": "victim@example.com", "password": "CorrectHorse1"}
            locked = await client.post("/api/v1/auth/login", json=correct)
            assert locked.status_code == 423, locked.text
            assert "Retry-After" in locked.headers
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_successful_login_resets_failure_counter(monkeypatch) -> None:
    await _reset_database()
    monkeypatch.setattr(config_module.settings, "AUTH_RATELIMIT_MAX_ATTEMPTS", 100)
    monkeypatch.setattr(config_module.settings, "AUTH_LOCKOUT_MAX_FAILED", 3)
    monkeypatch.setattr(config_module.settings, "AUTH_LOCKOUT_SECONDS", 900)
    try:
        async with _client() as client:
            reg = await client.post(
                "/api/v1/auth/register",
                json={"email": "comeback@example.com", "password": "CorrectHorse1", "full_name": "C"},
            )
            assert reg.status_code == 200, reg.text

            wrong = {"email": "comeback@example.com", "password": "bad"}
            correct = {"email": "comeback@example.com", "password": "CorrectHorse1"}

            # Two failures (below threshold), then a success resets the counter.
            assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
            assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
            assert (await client.post("/api/v1/auth/login", json=correct)).status_code == 200

            # Two more failures must NOT lock (counter was reset by the success).
            assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
            assert (await client.post("/api/v1/auth/login", json=wrong)).status_code == 401
            # Correct password still works -> not locked.
            assert (await client.post("/api/v1/auth/login", json=correct)).status_code == 200
    finally:
        await engine.dispose()
