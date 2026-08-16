"""GET /config/llm-status reports engine state without leaking secrets (SPEC-023).

The UI uses this endpoint to *show* whether ANTHROPIC_API_KEY is set instead of
offering a writable field, because config.yaml is tracked in git.
"""
import json

import pytest

from app.core import config as app_config
from app.routers.config import get_llm_status

# Synthetic sentinel, deliberately NOT shaped like a real credential so the
# secret scanner (gitleaks) has nothing to flag. Its only job is to be a
# distinctive string we can assert never appears in the response.
SECRET = "SENTINEL-CREDENTIAL-VALUE-DO-NOT-ECHO"


@pytest.mark.asyncio
async def test_reports_key_present_without_ever_returning_it(monkeypatch):
    monkeypatch.setattr(app_config.settings, "ANTHROPIC_API_KEY", SECRET, raising=False)
    monkeypatch.setattr(app_config.settings, "LLM_PROVIDER", "anthropic", raising=False)

    out = await get_llm_status(token_data=None)

    assert out["anthropic"]["api_key_set"] is True
    # The whole payload must not contain the secret in any form.
    assert SECRET not in json.dumps(out)


@pytest.mark.asyncio
async def test_reports_key_absent(monkeypatch):
    monkeypatch.setattr(app_config.settings, "ANTHROPIC_API_KEY", "", raising=False)

    out = await get_llm_status(token_data=None)

    assert out["anthropic"]["api_key_set"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("provider", ["anthropic", "ollama", "openai"])
async def test_reports_active_provider(monkeypatch, provider):
    monkeypatch.setattr(app_config.settings, "LLM_PROVIDER", provider, raising=False)

    out = await get_llm_status(token_data=None)

    assert out["provider"] == provider


@pytest.mark.asyncio
async def test_openai_key_presence_is_also_boolean_only(monkeypatch):
    monkeypatch.setattr(app_config.settings, "OPENAI_API_KEY", "SENTINEL-OPENAI-VALUE-DO-NOT-ECHO", raising=False)

    out = await get_llm_status(token_data=None)

    assert out["openai"]["api_key_set"] is True
    assert "SENTINEL-OPENAI-VALUE-DO-NOT-ECHO" not in json.dumps(out)


@pytest.mark.asyncio
async def test_exposes_default_model_for_the_ui(monkeypatch):
    monkeypatch.setattr(app_config.settings, "ANTHROPIC_MODEL", "claude-opus-5", raising=False)

    out = await get_llm_status(token_data=None)

    assert out["anthropic"]["model"] == "claude-opus-5"
