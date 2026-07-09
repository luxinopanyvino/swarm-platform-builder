"""Secret-hardening tests for T3.2 (#164).

Covers two guarantees:

1. `_validate_settings` fails fast (ValueError) in production (DEBUG=False) when
   SECRET_KEY is empty, too short, or a committed weak placeholder — and accepts
   a strong key. In DEBUG mode a weak key is tolerated (dev convenience).
2. `docker-compose.yml` contains no hardcoded secret literals: the sensitive
   values are injected via `${VAR:?...}` guards instead.
"""
import re
from pathlib import Path

import pytest

from app.core import config as config_module
from app.core.config import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def _settings(secret_key: str, debug: bool) -> Settings:
    return Settings(SECRET_KEY=secret_key, DEBUG=debug)


# ── SECRET_KEY validation ───────────────────────────────────────────────────

WEAK_KEYS = [
    "",
    "short",
    "local-dev-secret-key-change-in-production",  # committed docker-compose value
    "your-secret-key-change-in-production",       # committed .env.example value
    "CAMBIA-ESTO-EN-PRODUCCION-usa-openssl-rand-hex-32",  # committed config.yaml
    "changeme",
    "change-me-please-in-production-now",
    "this-is-a-placeholder-secret-key-value",
    "postgres:password@localhost",
    "x" * 31,  # one char below the minimum length
]


@pytest.mark.parametrize("weak", WEAK_KEYS)
def test_weak_secret_key_rejected_in_production(weak: str) -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        config_module._validate_settings(_settings(weak, debug=False))


@pytest.mark.parametrize("weak", WEAK_KEYS)
def test_weak_secret_key_allowed_in_debug(weak: str) -> None:
    # DEBUG mode is dev-only: weak keys must not abort startup.
    config_module._validate_settings(_settings(weak, debug=True))


def test_strong_secret_key_accepted_in_production() -> None:
    # 64 hex chars, as produced by `openssl rand -hex 32`.
    strong = "a3f5c9e1b7d20486fe1c9a5b3d7e2048c6f1a9b3d5e7028416a9c3b5d7e10248f"
    config_module._validate_settings(_settings(strong, debug=False))


def test_ci_debug_key_still_works() -> None:
    # The value used by the existing test/CI env with DEBUG=true must keep working.
    config_module._validate_settings(_settings("ci-secret-not-for-prod", debug=True))


# ── docker-compose.yml: no hardcoded secrets ────────────────────────────────

FORBIDDEN_LITERALS = [
    "POSTGRES_PASSWORD: password",
    "postgres:password@",
    "local-dev-secret-key-change-in-production",
    "minioadmin",
    ":password@",  # inline password in any URL (redis/postgres)
]


def test_compose_has_no_hardcoded_secret_literals() -> None:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    for literal in FORBIDDEN_LITERALS:
        assert literal not in text, (
            f"docker-compose.yml still contains a hardcoded secret literal: {literal!r}. "
            "Inject it via ${VAR:?...} from the environment instead."
        )


def test_compose_injects_required_secrets_with_guards() -> None:
    text = COMPOSE_FILE.read_text(encoding="utf-8")
    # Each secret must be sourced from the environment with a `:?` required guard.
    for var in ("SECRET_KEY", "POSTGRES_PASSWORD"):
        assert re.search(rf"\$\{{{var}:\?", text), (
            f"{var} must be injected from the environment with a required "
            f"guard, e.g. ${{{var}:?...}}"
        )
