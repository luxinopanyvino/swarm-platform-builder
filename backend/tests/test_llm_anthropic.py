"""Tests for the Anthropic (Claude) provider of the LLM dispatcher (SPEC-023).

Covers T12.1 acceptance criteria without a real LLM or the ``anthropic`` package:
- AC1: requests route to the official SDK with ``system`` as a top-level param
  and ``max_tokens`` fixed; text is extracted from the message content blocks.
- AC5: error classification (auth = permanent, no key in the message; 429/5xx/
  connection = transient) and the lazy missing-key error (permanent, no start-up
  abort — validated at first call).

The ``anthropic`` SDK is not installed in the test environment; each test injects
a fake module into ``sys.modules['anthropic']`` so the late ``from anthropic
import ...`` inside the provider picks it up.
"""
import sys
import types

import pytest

import app.platform.llm as llm
from app.platform.llm import TransientLLMError


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #

def _make_fake_anthropic():
    """Build a fake ``anthropic`` module mirroring the SDK error hierarchy."""
    mod = types.ModuleType("anthropic")

    class APIError(Exception):
        def __init__(self, message="", status_code=None):
            super().__init__(message)
            self.status_code = status_code

    class APIConnectionError(APIError):
        pass

    class APIStatusError(APIError):
        pass

    class AuthenticationError(APIStatusError):
        def __init__(self, message="authentication error", status_code=401):
            super().__init__(message, status_code)

    class RateLimitError(APIStatusError):
        def __init__(self, message="rate limited", status_code=429):
            super().__init__(message, status_code)

    mod.APIError = APIError
    mod.APIConnectionError = APIConnectionError
    mod.APIStatusError = APIStatusError
    mod.AuthenticationError = AuthenticationError
    mod.RateLimitError = RateLimitError
    mod.AsyncAnthropic = None  # each test sets this
    return mod


class _TextBlock:
    type = "text"

    def __init__(self, text):
        self.text = text


class _ToolUseBlock:
    type = "tool_use"

    def __init__(self, name, inp, id):
        self.name = name
        self.input = inp
        self.id = id


class _FakeMessage:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


def _client_factory(*, on_create=None, on_stream=None, recorder=None):
    """Return an AsyncAnthropic-shaped fake class driven by callbacks."""

    class _Messages:
        async def create(self, **kwargs):
            if recorder is not None:
                recorder["create"] = kwargs
            return on_create(**kwargs)

        def stream(self, **kwargs):
            if recorder is not None:
                recorder["stream"] = kwargs
            return on_stream(**kwargs)

    class FakeClient:
        def __init__(self, **kwargs):
            if recorder is not None:
                recorder["init"] = kwargs

        @property
        def messages(self):
            return _Messages()

        async def close(self):
            if recorder is not None:
                recorder["closed"] = True

    return FakeClient


def _install(monkeypatch, fake, *, api_key="sk-secret-XYZ", max_tokens=4096, base_url=None):
    from app.core import config
    monkeypatch.setattr(config.settings, "ANTHROPIC_API_KEY", api_key, raising=False)
    monkeypatch.setattr(config.settings, "ANTHROPIC_MAX_TOKENS", max_tokens, raising=False)
    monkeypatch.setattr(config.settings, "ANTHROPIC_BASE_URL", base_url, raising=False)
    monkeypatch.setitem(sys.modules, "anthropic", fake)


# --------------------------------------------------------------------------- #
# AC1 — routing & SDK mapping
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_call_anthropic_maps_system_and_max_tokens(monkeypatch):
    fake = _make_fake_anthropic()
    recorder = {}

    def on_create(**kwargs):
        return _FakeMessage([_TextBlock("Hola "), _TextBlock("mundo")])

    fake.AsyncAnthropic = _client_factory(on_create=on_create, recorder=recorder)
    _install(monkeypatch, fake, max_tokens=4096)

    out = await llm._call_anthropic(
        prompt="P", model="claude-opus-5", timeout=30.0, system_prompt="S"
    )

    assert out == "Hola mundo"                     # text blocks concatenated + stripped
    created = recorder["create"]
    assert created["model"] == "claude-opus-5"
    assert created["max_tokens"] == 4096           # required by the API
    assert created["system"] == "S"                # system as top-level param, not a turn
    assert created["messages"] == [{"role": "user", "content": "P"}]
    assert recorder["closed"] is True              # client always closed


@pytest.mark.asyncio
async def test_call_llm_routes_to_anthropic_and_uses_default_model(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)
    monkeypatch.setattr(config.settings, "ANTHROPIC_MODEL", "claude-opus-5", raising=False)

    seen = {}

    # `temperature` la añadió SPEC-014/T9.4: el doble refleja la firma real.
    async def fake_call(prompt, model, timeout, system_prompt=None, temperature=None):
        seen["model"] = model
        seen["prompt"] = prompt
        seen["temperature"] = temperature
        return "routed-ok"

    monkeypatch.setattr(llm, "_call_anthropic", fake_call)

    out = await llm.call_llm("hola")

    assert out == "routed-ok"
    # Y sin pedirla, no se fija: el defecto del proveedor se respeta.
    assert seen["temperature"] is None
    # get_default_model() resolves to ANTHROPIC_MODEL when the provider is anthropic.
    assert seen["model"] == "claude-opus-5"


@pytest.mark.asyncio
async def test_call_anthropic_stream_yields_text_deltas(monkeypatch):
    fake = _make_fake_anthropic()

    class _Stream:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        @property
        def text_stream(self):
            async def _gen():
                for tok in ["Ho", "la", " mundo"]:
                    yield tok
            return _gen()

    fake.AsyncAnthropic = _client_factory(on_stream=lambda **k: _Stream())
    _install(monkeypatch, fake)

    tokens = [
        t
        async for t in llm._call_anthropic_stream(
            prompt="P", model="m", timeout=30.0, system_prompt="S"
        )
    ]
    assert "".join(tokens) == "Hola mundo"


@pytest.mark.asyncio
async def test_tool_loop_anthropic_executes_tool_then_returns_text(monkeypatch):
    from app.core import config
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)

    fake = _make_fake_anthropic()
    calls = {"n": 0}

    def on_create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _FakeMessage(
                [_ToolUseBlock("get_x", {"a": 1}, "tu_1")], stop_reason="tool_use"
            )
        # second round: the tool result was fed back; model answers in plain text
        return _FakeMessage([_TextBlock("done")], stop_reason="end_turn")

    fake.AsyncAnthropic = _client_factory(on_create=on_create)
    _install(monkeypatch, fake)

    seen = {}

    async def executor(name, args):
        seen["name"] = name
        seen["args"] = args
        return "42"

    schemas = [{
        "type": "function",
        "function": {"name": "get_x", "description": "d", "parameters": {"type": "object", "properties": {}}},
    }]

    out = await llm.call_llm_with_tools("SYS", "USER", schemas, executor, model="m")

    assert out == "done"
    assert seen["name"] == "get_x"
    assert seen["args"] == {"a": 1}


def test_to_anthropic_tools_converts_openai_function_schema():
    schemas = [{
        "type": "function",
        "function": {
            "name": "search",
            "description": "web search",
            "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
        },
    }]
    out = llm._to_anthropic_tools(schemas)
    assert out == [{
        "name": "search",
        "description": "web search",
        "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
    }]


# --------------------------------------------------------------------------- #
# AC5 — error classification & lazy missing key
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_missing_key_is_permanent_and_lazy(monkeypatch):
    fake = _make_fake_anthropic()
    _install(monkeypatch, fake, api_key="")  # no key configured

    with pytest.raises(RuntimeError) as ei:
        await llm._call_anthropic(prompt="P", model="claude-opus-5", timeout=30.0)

    assert "ANTHROPIC_API_KEY" in str(ei.value)
    assert not isinstance(ei.value, TransientLLMError)  # permanent → not retried


@pytest.mark.asyncio
async def test_auth_error_is_permanent_without_leaking_key(monkeypatch):
    fake = _make_fake_anthropic()

    def on_create(**kwargs):
        raise fake.AuthenticationError("401 invalid x-api-key sk-secret-XYZ")

    fake.AsyncAnthropic = _client_factory(on_create=on_create)
    _install(monkeypatch, fake, api_key="sk-secret-XYZ")

    with pytest.raises(RuntimeError) as ei:
        await llm._call_anthropic(prompt="P", model="m", timeout=30.0)

    assert not isinstance(ei.value, TransientLLMError)
    assert "sk-secret-XYZ" not in str(ei.value)  # AC5: never echo the key


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["rate_limit", "connection", "status_503"])
async def test_transient_errors_are_retryable(monkeypatch, kind):
    fake = _make_fake_anthropic()

    def on_create(**kwargs):
        if kind == "rate_limit":
            raise fake.RateLimitError()
        if kind == "connection":
            raise fake.APIConnectionError("all connection attempts failed")
        raise fake.APIStatusError("server error", status_code=503)

    fake.AsyncAnthropic = _client_factory(on_create=on_create)
    _install(monkeypatch, fake)

    with pytest.raises(TransientLLMError):
        await llm._call_anthropic(prompt="P", model="m", timeout=30.0)


@pytest.mark.asyncio
async def test_4xx_status_is_permanent(monkeypatch):
    fake = _make_fake_anthropic()

    def on_create(**kwargs):
        raise fake.APIStatusError("bad request", status_code=400)

    fake.AsyncAnthropic = _client_factory(on_create=on_create)
    _install(monkeypatch, fake)

    with pytest.raises(RuntimeError) as ei:
        await llm._call_anthropic(prompt="P", model="m", timeout=30.0)
    assert not isinstance(ei.value, TransientLLMError)


@pytest.mark.asyncio
async def test_empty_response_is_transient(monkeypatch):
    fake = _make_fake_anthropic()

    def on_create(**kwargs):
        return _FakeMessage([])  # no text blocks

    fake.AsyncAnthropic = _client_factory(on_create=on_create)
    _install(monkeypatch, fake)

    with pytest.raises(TransientLLMError):
        await llm._call_anthropic(prompt="P", model="m", timeout=30.0)


# --------------------------------------------------------------------------- #
# temperature — añadida en SPEC-014/T9.4 para el juez de las evals
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_temperature_no_se_envia_cuando_no_se_pide(monkeypatch):
    """El defecto tiene que ser invisible: los agentes ya en producción no
    pueden cambiar de comportamiento porque el harness necesitara un parámetro."""
    fake = _make_fake_anthropic()
    recorder = {}
    fake.AsyncAnthropic = _client_factory(
        on_create=lambda **kw: _FakeMessage([_TextBlock("ok")]), recorder=recorder
    )
    _install(monkeypatch, fake)

    await llm._call_anthropic(prompt="P", model="claude-opus-5", timeout=30.0)
    assert "temperature" not in recorder["create"]


@pytest.mark.asyncio
async def test_temperature_llega_al_proveedor_cuando_se_pide(monkeypatch):
    """SPEC-014 §5 exige el juez a `temperature=0`. Antes de esto el dispatcher
    no aceptaba el parámetro: los perfiles lo guardaban y nunca llegaba a nadie."""
    from app.core import config
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)

    fake = _make_fake_anthropic()
    recorder = {}
    fake.AsyncAnthropic = _client_factory(
        on_create=lambda **kw: _FakeMessage([_TextBlock("ok")]), recorder=recorder
    )
    _install(monkeypatch, fake)

    await llm.call_llm("P", model="claude-opus-5", temperature=0)
    assert recorder["create"]["temperature"] == 0
