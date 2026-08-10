"""Structured logging + request correlation (SPEC-019 / T5.1).

Central logging setup for the backend:

* **JSON** logs in production (``timestamp``, ``level``, ``logger``, ``message``,
  ``request_id`` + any contextual ``extra`` fields), or a **human-readable** line
  when ``DEBUG`` is on (SPEC-019: readable in dev, machine-parseable in prod).
* A **correlation id** (``request_id``) propagated per request via a
  ``ContextVar`` and injected into every log record by a filter; the ASGI
  middleware (``request_id_middleware``) sets it from the ``X-Request-ID`` header
  (or a fresh uuid) and echoes it back on the response.
* **No emojis at INFO+**: emoji/pictographs are stripped from the message for
  records at ``INFO`` and above, so operational logs stay clean; ``DEBUG`` keeps
  them for local ergonomics.

Configure once at startup with :func:`configure_logging`.
"""
from __future__ import annotations

import json
import logging
import re
import sys
from contextvars import ContextVar
from datetime import datetime, timezone
from uuid import uuid4

# Correlation id for the current request/task. "-" when outside a request.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")

# Broad emoji / pictograph / symbol ranges (incl. variation selectors and
# regional indicators). Deliberately conservative: strips decoration, not text.
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF"   # symbols & pictographs, emoticons, transport, etc.
    "\U00002600-\U000027BF"    # misc symbols (2600-26FF) + dingbats (2700-27BF): ✅ ❌
    "\U0001F1E6-\U0001F1FF"    # regional indicators
    "\U00002B00-\U00002BFF"    # misc symbols and arrows (pictographic)
    "\U0000FE00-\U0000FE0F"    # variation selectors
    "]",
    flags=re.UNICODE,
)

# Standard LogRecord attributes — everything else in record.__dict__ is a
# caller-supplied ``extra`` and gets promoted to a top-level JSON field.
_RESERVED_RECORD_KEYS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "request_id", "message", "asctime",
}


def strip_emojis(text: str) -> str:
    """Remove emoji/pictograph characters and tidy the surrounding whitespace."""
    return _EMOJI_RE.sub("", text).strip()


def _clean_message(record: logging.LogRecord) -> str:
    """Rendered message, with emojis removed at INFO and above."""
    msg = record.getMessage()
    if record.levelno >= logging.INFO:
        msg = strip_emojis(msg)
    return msg


class RequestIdFilter(logging.Filter):
    """Inject the current ``request_id`` onto every record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _clean_message(record),
            "request_id": getattr(record, "request_id", "-"),
        }
        # Promote contextual extras (logger.info("x", extra={...})).
        for key, value in record.__dict__.items():
            if key not in _RESERVED_RECORD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class HumanFormatter(logging.Formatter):
    """Readable single line for local development (still emoji-free at INFO+)."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, timezone.utc).strftime("%H:%M:%S")
        rid = getattr(record, "request_id", "-")
        line = f"{ts} {record.levelname:<7} [{rid}] {record.name}: {_clean_message(record)}"
        if record.exc_info:
            line = f"{line}\n{self.formatException(record.exc_info)}"
        return line


def configure_logging(debug: bool | None = None) -> None:
    """Install the root logging handler (idempotent).

    JSON in production; human-readable when ``debug`` (defaults to
    ``settings.DEBUG``). Safe to call more than once — handlers are reset.
    """
    if debug is None:
        from app.core.config import settings  # lazy: avoids import cycle
        debug = settings.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(HumanFormatter() if debug else JsonFormatter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)

    # Keep third-party access/transport logs from drowning the signal.
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def request_id_middleware(request, call_next):
    """ASGI middleware: bind a correlation id for the request's lifetime.

    Reuses an inbound ``X-Request-ID`` (so a gateway/client id is preserved) or
    mints a fresh one, exposes it to logs via ``request_id_ctx`` for the whole
    request, and echoes it back on the response header.
    """
    incoming = request.headers.get("X-Request-ID")
    rid = incoming.strip() if incoming and incoming.strip() else uuid4().hex
    token = request_id_ctx.set(rid)
    try:
        response = await call_next(request)
    finally:
        request_id_ctx.reset(token)
    try:
        response.headers["X-Request-ID"] = rid
    except Exception:  # pragma: no cover - defensive; some responses lack headers
        pass
    return response
