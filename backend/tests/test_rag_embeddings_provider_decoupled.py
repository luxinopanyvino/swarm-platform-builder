"""Embeddings are decoupled from the generation provider — SPEC-023 / T12.4 / AC6.

Anthropic offers no embeddings API, so with ``LLM_PROVIDER=anthropic`` the RAG
must keep using its own embeddings provider (Ollama by default, OpenAI when the
provider is openai) instead of trying — and failing — to embed via Anthropic.
"""
import pytest

import app.platform.capabilities.rag as rag
from app.core import config


@pytest.fixture
def _spy_embedding_backends(monkeypatch):
    """Replace the two concrete embedders with spies that record the route taken."""
    called = {"route": None}

    async def fake_ollama(text, ollama_base_url, model):
        called["route"] = "ollama"
        return [0.1, 0.2, 0.3]

    async def fake_openai(text):
        called["route"] = "openai"
        return [0.4, 0.5, 0.6]

    monkeypatch.setattr(rag, "_get_embedding_ollama", fake_ollama)
    monkeypatch.setattr(rag, "_get_embedding_openai", fake_openai)
    return called


@pytest.mark.asyncio
async def test_anthropic_provider_embeds_via_ollama_not_anthropic(monkeypatch, _spy_embedding_backends):
    """With the default anthropic engine, embeddings route to Ollama (never Anthropic)."""
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)

    vec = await rag.get_embedding("hola", "http://localhost:11434", "nomic-embed-text")

    assert _spy_embedding_backends["route"] == "ollama"
    assert vec == [0.1, 0.2, 0.3]


@pytest.mark.asyncio
async def test_openai_provider_embeds_via_openai(monkeypatch, _spy_embedding_backends):
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "openai", raising=False)

    await rag.get_embedding("hola", "http://localhost:11434", "nomic-embed-text")

    assert _spy_embedding_backends["route"] == "openai"


@pytest.mark.asyncio
async def test_ollama_provider_embeds_via_ollama(monkeypatch, _spy_embedding_backends):
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "ollama", raising=False)

    await rag.get_embedding("hola", "http://localhost:11434", "nomic-embed-text")

    assert _spy_embedding_backends["route"] == "ollama"
