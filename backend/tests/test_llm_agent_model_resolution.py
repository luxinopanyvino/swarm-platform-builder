"""Tests for provider-aware per-agent model resolution (SPEC-023 / T12.3).

- AC4: under the anthropic provider each core agent resolves to its mapped Claude
  model (investigador→opus-5, redactor/revisor→sonnet-5, formateador→haiku-4-5).
- AC3: the same agent resolves to different models under different providers, via
  the cascade agent_settings.model → .agent.md models[provider] → legacy model
  (namespace-matched) → get_default_model().

These read the real .agent.md files under app/agents (tests run from backend/).
"""
import pytest

import app.platform.llm as llm
from app.core import config


@pytest.mark.parametrize(
    "agent,expected",
    [
        ("investigador", "claude-opus-5"),
        ("redactor", "claude-sonnet-5"),
        ("revisor", "claude-sonnet-5"),
        ("formateador", "claude-haiku-4-5"),
    ],
)
def test_anthropic_mapping_per_agent(monkeypatch, agent, expected):
    """AC4 — anthropic default maps each core agent to its Claude model."""
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)
    assert llm.resolve_agent_model(agent, {}) == expected


def test_anthropic_ignores_legacy_ollama_override(monkeypatch):
    """A legacy Ollama value seeded in the DB does not hijack the anthropic default."""
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)
    agent_settings = {"redactor": {"model": "llama3.2:3b"}}  # legacy, namespace=ollama
    assert llm.resolve_agent_model("redactor", agent_settings) == "claude-sonnet-5"


def test_same_agent_resolves_differently_per_provider(monkeypatch):
    """AC3 — provider switch yields a different model for the same agent."""
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)
    anthropic_model = llm.resolve_agent_model("investigador", {})

    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "ollama", raising=False)
    ollama_model = llm.resolve_agent_model("investigador", {})

    assert anthropic_model == "claude-opus-5"
    assert ollama_model == "mistral:7b"
    assert anthropic_model != ollama_model


def test_explicit_override_wins_when_namespace_matches(monkeypatch):
    """Cascade step 1: an override whose namespace matches the provider is used."""
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)
    m = llm.resolve_agent_model("redactor", {"redactor": {"model": "claude-opus-5"}})
    assert m == "claude-opus-5"  # beats models[anthropic] = claude-sonnet-5


def test_falls_back_to_provider_default_when_unmapped(monkeypatch):
    """Cascade step 4: no models[provider] and a mismatched legacy → global default."""
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "openai", raising=False)
    monkeypatch.setattr(config.settings, "OPENAI_MODEL", "gpt-4o-mini", raising=False)
    # formateador maps anthropic+ollama only; legacy llama3.2:1b is ollama, not openai.
    assert llm.resolve_agent_model("formateador", {}) == "gpt-4o-mini"


def test_unknown_agent_uses_provider_default(monkeypatch):
    monkeypatch.setattr(config.settings, "LLM_PROVIDER", "anthropic", raising=False)
    monkeypatch.setattr(config.settings, "ANTHROPIC_MODEL", "claude-opus-5", raising=False)
    assert llm.resolve_agent_model("does-not-exist", {}) == "claude-opus-5"


@pytest.mark.parametrize(
    "model,namespace",
    [
        ("claude-opus-5", "anthropic"),
        ("claude-haiku-4-5", "anthropic"),
        ("gpt-4o-mini", "openai"),
        ("o3-mini", "openai"),
        ("mistral:7b", "ollama"),
        ("llama3.2:3b", "ollama"),
        ("", "ollama"),
    ],
)
def test_model_namespace_detection(model, namespace):
    assert llm._model_namespace(model) == namespace
