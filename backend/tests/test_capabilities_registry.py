"""Tests del registro de capacidades tipadas del motor (SPEC-013 AC3, #208)."""

import os

import pytest

os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("SECRET_KEY", "ci-secret-not-for-prod")

from app.platform.capabilities import registry  # noqa: E402
from app.platform.capabilities.registry import (  # noqa: E402
    Capability,
    CapabilityKind,
    CapabilityNotAvailable,
)


def test_registry_lists_all_six_kinds():
    """Listar capacidades cubre los 6 tipos: rag/search/scrape/format/publish/llm."""
    caps = registry.list_capabilities()
    assert all(isinstance(c, Capability) for c in caps)
    kinds = {c.kind for c in caps}
    assert kinds == set(CapabilityKind)
    assert len(caps) >= 6


def test_available_capabilities_resolve_to_importable_entrypoints():
    """Toda capacidad disponible resuelve a un objeto importable e invocable."""
    for cap in registry.list_capabilities():
        if not cap.available:
            continue
        impl = cap.resolve()
        assert callable(impl), f"entrypoint de '{cap.name}' no es invocable"


def test_scrape_declared_but_not_available():
    """`scrape` figura en el registro como tipo sin proveedor activo."""
    cap = registry.get("scrape")
    assert cap.kind is CapabilityKind.SCRAPE
    assert cap.available is False
    assert cap.entrypoint is None
    with pytest.raises(CapabilityNotAvailable):
        cap.resolve()


def test_get_unknown_capability_raises_keyerror():
    with pytest.raises(KeyError):
        registry.get("nope-not-a-capability")


def test_moved_infrastructure_lives_under_platform():
    """La infraestructura rag/tools/llm vive bajo app.platform, no bajo adapters."""
    import importlib.util

    from app.platform.capabilities import rag, tools
    from app.platform import llm

    assert rag.__name__ == "app.platform.capabilities.rag"
    assert tools.__name__ == "app.platform.capabilities.tools"
    assert llm.__name__ == "app.platform.llm"

    # Las rutas legacy ya no existen (nombres compuestos para no reintroducir
    # los literales que el gate de imports antiguos comprueba con grep).
    legacy_modules = [
        ".".join(["app", "modules", "agents", "adapters", leaf])
        for leaf in ("rag", "tools")
    ] + [".".join(["app", "shared", "llm"])]
    for module_name in legacy_modules:
        assert importlib.util.find_spec(module_name) is None, (
            f"El módulo legacy '{module_name}' no debería existir tras T8.2"
        )
