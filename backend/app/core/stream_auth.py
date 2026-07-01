"""Single-use, short-lived tickets to authenticate SSE stream connections (T1.4).

The browser ``EventSource`` API cannot send an ``Authorization`` header, so the
agent-run stream previously accepted the JWT in the query string
(``/stream?token=<JWT>``). That leaks a long-lived credential into server logs,
browser history and proxy logs. Instead, an already-authenticated client
exchanges its JWT (sent as a normal Bearer header on a POST) for an opaque
**ticket**, and connects to the stream with ``?ticket=<ticket>``. A leaked
ticket is near-useless: it expires within seconds and is consumed on first use.

The store is in-process (like ``active_streams``); a multi-worker deployment
should back it with a shared store (Redis) — see task T4.3 (#170).
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

DEFAULT_TTL_SECONDS = 30


@dataclass
class _Ticket:
    user_id: str
    article_id: str
    expires_at: float  # time.monotonic() deadline


_tickets: dict[str, _Ticket] = {}


def _purge_expired(now: float) -> None:
    for key in [k for k, t in _tickets.items() if t.expires_at <= now]:
        _tickets.pop(key, None)


def issue_ticket(user_id: str, article_id: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    """Mint a one-time ticket binding *user_id* to *article_id* for a short TTL."""
    now = time.monotonic()
    _purge_expired(now)
    ticket = secrets.token_urlsafe(32)
    _tickets[ticket] = _Ticket(
        user_id=str(user_id),
        article_id=str(article_id),
        expires_at=now + max(1, ttl_seconds),
    )
    return ticket


def consume_ticket(ticket: str, article_id: str) -> str | None:
    """Return the bound ``user_id`` if *ticket* is valid for *article_id*, else None.

    The ticket is **single-use**: it is removed on any consume attempt (valid or
    not) so it cannot be replayed.
    """
    if not ticket:
        return None
    entry = _tickets.pop(ticket, None)
    if entry is None:
        return None
    if entry.expires_at <= time.monotonic():
        return None
    if entry.article_id != str(article_id):
        return None
    return entry.user_id


def reset_stream_tickets() -> None:
    """Clear all outstanding tickets (used by tests to isolate cases)."""
    _tickets.clear()
