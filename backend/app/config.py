"""Compatibility wrapper: expose `settings` from core.config at `app.config`."""
from .core.config import settings, Settings  # re-export

__all__ = ["settings", "Settings"]
