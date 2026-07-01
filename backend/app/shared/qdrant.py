"""Helpers to talk to Qdrant with authentication (T3.1).

Qdrant is an internal service; when it is protected with an API key
(``settings.QDRANT_API_KEY`` / the ``QDRANT__SERVICE__API_KEY`` env on the Qdrant
container) every request must carry the ``api-key`` header. Centralising client
construction here guarantees no call-site forgets it.
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings


def qdrant_headers(api_key: Optional[str] = None) -> dict:
    """Return the auth header for Qdrant, or an empty dict when no key is set.

    ``api_key`` defaults to ``settings.QDRANT_API_KEY``; pass it explicitly when a
    caller already threads the key through its own arguments.
    """
    key = api_key if api_key is not None else settings.QDRANT_API_KEY
    return {"api-key": key} if key else {}


def qdrant_client(timeout: float = 10.0, api_key: Optional[str] = None) -> httpx.AsyncClient:
    """An ``httpx.AsyncClient`` pointed at Qdrant with the auth header applied."""
    return httpx.AsyncClient(
        base_url=settings.QDRANT_URL,
        timeout=timeout,
        headers=qdrant_headers(api_key),
    )
