"""Structured logging + correlation id (SPEC-019 / T5.1 / AC1)."""
import json
import logging

import pytest

from app.core import logging_config as lc


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _record(msg, level=logging.INFO, name="test.logger", **extra):
    rec = logging.LogRecord(name, level, __file__, 10, msg, None, None)
    for k, v in extra.items():
        setattr(rec, k, v)
    lc.RequestIdFilter().filter(rec)  # inject request_id like the handler does
    return rec


# --------------------------------------------------------------------------- #
# JSON formatter
# --------------------------------------------------------------------------- #

def test_json_formatter_emits_valid_json_with_required_fields():
    out = lc.JsonFormatter().format(_record("hola mundo"))
    payload = json.loads(out)  # must be a single valid JSON object
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test.logger"
    assert payload["message"] == "hola mundo"
    assert "timestamp" in payload and "T" in payload["timestamp"]
    assert payload["request_id"] == "-"  # no request bound


def test_json_formatter_includes_request_id_from_contextvar():
    token = lc.request_id_ctx.set("req-123")
    try:
        payload = json.loads(lc.JsonFormatter().format(_record("x")))
    finally:
        lc.request_id_ctx.reset(token)
    assert payload["request_id"] == "req-123"


def test_json_formatter_promotes_contextual_extra_fields():
    payload = json.loads(lc.JsonFormatter().format(_record("x", agent="redactor", tokens=42)))
    assert payload["agent"] == "redactor"
    assert payload["tokens"] == 42


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        rec = logging.LogRecord("t", logging.ERROR, __file__, 1, "fallo", None, sys.exc_info())
        lc.RequestIdFilter().filter(rec)
    payload = json.loads(lc.JsonFormatter().format(rec))
    assert "ValueError: boom" in payload["exc_info"]


# --------------------------------------------------------------------------- #
# Emoji policy (no emojis at INFO+, kept at DEBUG)
# --------------------------------------------------------------------------- #

def test_emojis_stripped_at_info_and_above():
    payload = json.loads(lc.JsonFormatter().format(_record("🔍 buscando ✅", level=logging.INFO)))
    assert payload["message"] == "buscando"


def test_emojis_kept_at_debug():
    payload = json.loads(lc.JsonFormatter().format(_record("🔍 buscando", level=logging.DEBUG)))
    assert "🔍" in payload["message"]


def test_strip_emojis_preserves_punctuation_and_arrows_text():
    # em-dash, ellipsis, accents must survive (they are not emojis)
    assert lc.strip_emojis("Etapa 2/2 — síntesis… ✅") == "Etapa 2/2 — síntesis…"


def test_human_formatter_is_emoji_free_at_info():
    line = lc.HumanFormatter().format(_record("🎉 listo", level=logging.WARNING))
    assert "🎉" not in line
    assert "listo" in line and "[-]" in line  # request_id shown


# --------------------------------------------------------------------------- #
# Correlation-id middleware (framework-agnostic)
# --------------------------------------------------------------------------- #

class _FakeRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


class _FakeResponse:
    def __init__(self):
        self.headers = {}


@pytest.mark.asyncio
async def test_middleware_mints_id_and_binds_context_then_resets():
    seen = {}

    async def call_next(_request):
        seen["during"] = lc.request_id_ctx.get()
        return _FakeResponse()

    resp = await lc.request_id_middleware(_FakeRequest(), call_next)

    assert seen["during"] not in ("-", None) and len(seen["during"]) >= 16  # a real id
    assert resp.headers["X-Request-ID"] == seen["during"]
    assert lc.request_id_ctx.get() == "-"  # reset after the request


@pytest.mark.asyncio
async def test_middleware_reuses_inbound_request_id():
    async def call_next(_request):
        assert lc.request_id_ctx.get() == "abc-123"
        return _FakeResponse()

    resp = await lc.request_id_middleware(_FakeRequest({"X-Request-ID": "abc-123"}), call_next)
    assert resp.headers["X-Request-ID"] == "abc-123"


@pytest.mark.asyncio
async def test_middleware_resets_context_even_on_error():
    async def call_next(_request):
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await lc.request_id_middleware(_FakeRequest(), call_next)
    assert lc.request_id_ctx.get() == "-"  # no leak into the next request
