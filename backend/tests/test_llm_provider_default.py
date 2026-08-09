"""Tests for the default LLM provider being Anthropic (Claude) — SPEC-023 / T12.2.

Covers AC2: the shipped default is ``anthropic`` and resolves to ANTHROPIC_MODEL,
while a deployment can switch back to ollama/openai purely by configuration
(env var beats config.yaml, which beats the code default) — no code change.
"""
import pytest

from app.core import config
from app.core.config import Settings


def test_code_default_provider_is_anthropic():
    """The Settings schema default (no config.yaml, no env) is Claude."""
    s = Settings()
    assert s.LLM_PROVIDER == "anthropic"
    assert s.ANTHROPIC_MODEL == "claude-opus-5"
    assert s.ANTHROPIC_MAX_TOKENS == 4096


def test_build_settings_default_provider_is_anthropic(monkeypatch):
    """With the committed config.yaml and no env override, the default is anthropic."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    s = config._build_settings()
    assert s.LLM_PROVIDER == "anthropic"


@pytest.mark.parametrize(
    "provider,expected_attr",
    [
        ("anthropic", "ANTHROPIC_MODEL"),
        ("ollama", "OLLAMA_MODEL"),
        ("openai", "OPENAI_MODEL"),
    ],
)
def test_get_default_model_follows_provider(monkeypatch, provider, expected_attr):
    """get_default_model() returns the model of the active provider."""
    import app.platform.llm as llm

    monkeypatch.setattr(config.settings, "LLM_PROVIDER", provider, raising=False)
    assert llm.get_default_model() == getattr(config.settings, expected_attr)


@pytest.mark.parametrize("provider", ["ollama", "openai"])
def test_switch_provider_via_env_without_code_change(monkeypatch, provider):
    """LLM_PROVIDER env var (highest precedence) switches away from the default."""
    monkeypatch.setenv("LLM_PROVIDER", provider)
    s = config._build_settings()
    assert s.LLM_PROVIDER == provider  # env beats config.yaml's 'anthropic'
