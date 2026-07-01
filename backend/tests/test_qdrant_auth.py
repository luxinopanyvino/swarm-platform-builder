"""Qdrant authentication helper tests (task T3.1, #163).

Ensures every Qdrant call carries the ``api-key`` header when a key is
configured, so an authenticated (and no longer host-exposed) Qdrant works.
"""

import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings  # noqa: E402
from app.shared.qdrant import qdrant_client, qdrant_headers  # noqa: E402


def test_headers_include_api_key_when_set(monkeypatch):
    monkeypatch.setattr(settings, "QDRANT_API_KEY", "s3cret")
    assert qdrant_headers() == {"api-key": "s3cret"}


def test_headers_empty_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "QDRANT_API_KEY", None)
    assert qdrant_headers() == {}
    monkeypatch.setattr(settings, "QDRANT_API_KEY", "")
    assert qdrant_headers() == {}


def test_headers_explicit_key_overrides_settings(monkeypatch):
    monkeypatch.setattr(settings, "QDRANT_API_KEY", "from-settings")
    assert qdrant_headers("explicit") == {"api-key": "explicit"}


@pytest.mark.asyncio
async def test_client_is_configured_with_auth_and_base_url(monkeypatch):
    monkeypatch.setattr(settings, "QDRANT_API_KEY", "s3cret")
    monkeypatch.setattr(settings, "QDRANT_URL", "http://qdrant:6333")
    client = qdrant_client()
    try:
        assert client.headers.get("api-key") == "s3cret"
        assert str(client.base_url) == "http://qdrant:6333"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_client_has_no_api_key_header_when_unset(monkeypatch):
    monkeypatch.setattr(settings, "QDRANT_API_KEY", None)
    client = qdrant_client()
    try:
        assert "api-key" not in client.headers
    finally:
        await client.aclose()
