"""Tests for the LLM resilience layer: retry of transient failures with backoff."""
import pytest

import app.shared.llm as llm
from app.shared.llm import TransientLLMError


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    # 3 retries, zero delay so tests don't actually sleep
    monkeypatch.setattr(llm, "_retry_params", lambda: (3, 0.0, 0.0))
    # Force the ollama provider path
    from app.core import config
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "ollama", raising=False)


@pytest.mark.asyncio
async def test_call_llm_retries_transient_then_succeeds(monkeypatch):
    attempts = {"n": 0}

    async def flaky(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise TransientLLMError("All connection attempts failed")
        return "ok"

    monkeypatch.setattr(llm, "_call_ollama", flaky)

    result = await llm.call_llm("hola")
    assert result == "ok"
    assert attempts["n"] == 3  # failed twice, succeeded on the third


@pytest.mark.asyncio
async def test_call_llm_does_not_retry_permanent_error(monkeypatch):
    attempts = {"n": 0}

    async def permanent(*args, **kwargs):
        attempts["n"] += 1
        raise RuntimeError("Ollama returned HTTP 404: model not found")

    monkeypatch.setattr(llm, "_call_ollama", permanent)

    with pytest.raises(RuntimeError):
        await llm.call_llm("hola")
    assert attempts["n"] == 1  # no retries on a permanent error


@pytest.mark.asyncio
async def test_call_llm_raises_after_exhausting_retries(monkeypatch):
    attempts = {"n": 0}

    async def always_transient(*args, **kwargs):
        attempts["n"] += 1
        raise TransientLLMError("All connection attempts failed")

    monkeypatch.setattr(llm, "_call_ollama", always_transient)

    with pytest.raises(TransientLLMError):
        await llm.call_llm("hola")
    assert attempts["n"] == 4  # 1 initial + 3 retries


@pytest.mark.asyncio
async def test_stream_retries_before_first_token(monkeypatch):
    attempts = {"n": 0}

    async def flaky_stream(*args, **kwargs):
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise TransientLLMError("connection refused")
            yield  # pragma: no cover — makes this an async generator
        for tok in ["Hola", " ", "mundo"]:
            yield tok

    monkeypatch.setattr(llm, "_call_ollama_stream", flaky_stream)

    tokens = [t async for t in llm.call_llm_stream("hola")]
    assert "".join(tokens) == "Hola mundo"
    assert attempts["n"] == 2  # retried the connection once


@pytest.mark.asyncio
async def test_stream_does_not_restart_after_first_token(monkeypatch):
    attempts = {"n": 0}

    async def break_midstream(*args, **kwargs):
        attempts["n"] += 1
        yield "primer"
        raise TransientLLMError("dropped mid-stream")

    monkeypatch.setattr(llm, "_call_ollama_stream", break_midstream)

    collected = []
    with pytest.raises(TransientLLMError):
        async for tok in llm.call_llm_stream("hola"):
            collected.append(tok)

    # Token already streamed; must NOT retry (would duplicate "primer")
    assert collected == ["primer"]
    assert attempts["n"] == 1
