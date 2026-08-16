"""Hot reload of configuration (SPEC-023 / Config screen).

``settings`` is built once at import, so saving config.yaml used to have no
effect until the process restarted — the Config screen silently promised a
change it never made. ``reload_settings()`` re-reads the file into the live
object.
"""
import textwrap

import pytest

from app.core import config as app_config
from app.core.config import reload_settings, settings


@pytest.fixture(autouse=True)
def _restore_settings():
    """Snapshot/restore the process-wide settings so cases don't leak."""
    before = settings.model_dump()
    yield
    for field, value in before.items():
        setattr(settings, field, value)


def _write_config(tmp_path, monkeypatch, provider="ollama", model="llama3.2:1b"):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        textwrap.dedent(f"""
        app:
          name: Test
          debug: true
        llm:
          provider: {provider}
        ollama:
          default_model: {model}
        """).strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("CONFIG_YAML_PATH", str(cfg))
    return cfg


def test_reload_picks_up_the_saved_file(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    _write_config(tmp_path, monkeypatch, provider="ollama")

    reload_settings()

    assert settings.LLM_PROVIDER == "ollama"


def test_reload_mutates_in_place_so_existing_references_see_it(tmp_path, monkeypatch):
    """Modules bind the object at import; rebinding the global would not reach them."""
    held_reference = settings  # what `from app.core.config import settings` captures
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    _write_config(tmp_path, monkeypatch, provider="ollama")

    reload_settings()

    assert held_reference.LLM_PROVIDER == "ollama"
    assert held_reference is app_config.settings  # same object, not a replacement


def test_reload_applies_nested_values_too(tmp_path, monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    _write_config(tmp_path, monkeypatch, provider="ollama", model="gemma2:2b")

    reload_settings()

    assert settings.OLLAMA_MODEL == "gemma2:2b"


def test_env_var_still_wins_after_reload(tmp_path, monkeypatch):
    """Precedence (env > config.yaml > defaults) must survive a reload."""
    _write_config(tmp_path, monkeypatch, provider="ollama")
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")

    reload_settings()

    assert settings.LLM_PROVIDER == "anthropic"


def test_invalid_config_raises_and_leaves_live_settings_untouched(tmp_path, monkeypatch):
    """A rejected file must not half-apply: the running config stays as it was."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    _write_config(tmp_path, monkeypatch, provider="ollama")
    reload_settings()
    assert settings.LLM_PROVIDER == "ollama"

    # debug=false + placeholder SECRET_KEY → _validate_settings rejects it.
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        textwrap.dedent("""
        app:
          debug: false
        security:
          secret_key: change-me
        llm:
          provider: openai
        """).strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("CONFIG_YAML_PATH", str(bad))
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    with pytest.raises(ValueError):
        reload_settings()

    # Unchanged — not switched to the rejected file's provider.
    assert settings.LLM_PROVIDER == "ollama"
