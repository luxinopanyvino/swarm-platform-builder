"""Shared pytest fixtures for the backend test-suite."""
import sys
from pathlib import Path

import pytest

# Ensure the backend package is importable when pytest is invoked from repo root.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from app.core.rate_limit import reset_auth_throttling  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_auth_throttling():
    """Keep auth rate-limit / lockout state isolated between tests.

    The throttling stores are process-wide singletons; without this reset, hits
    from one test would leak into the next and make the suite order-dependent.
    """
    reset_auth_throttling()
    yield
    reset_auth_throttling()
