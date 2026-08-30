"""Liveness, readiness y salud del despliegue (SPEC-019/T5.4/AC4 + SPEC-017/T3.5/AC5).

AC4: `/health` distingue **liveness** (proceso vivo) de **readiness** (BD, Qdrant y
proveedor de LLM alcanzables), devolviendo `503` con el detalle de la dependencia
caída.

AC5: los servicios del compose declaran límites de recursos y healthchecks de
**readiness** además de liveness.

La distinción no es cosmética y por eso hay tests que la fijan: si el liveness
mirase dependencias, una caída de Postgres haría que el orquestador reiniciara el
backend en bucle sin arreglar nada.
"""
import os
import sys
from pathlib import Path

import pytest
import yaml
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_health.db").resolve()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}")

from app.core.config import settings  # noqa: E402
from app.routers import health as health_router  # noqa: E402

COMPOSE = REPO_DIR / "docker-compose.yml"


@pytest.fixture
def client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
def todo_ok(monkeypatch):
    """Las tres dependencias responden."""
    async def ok():
        return "ok", None

    monkeypatch.setattr(health_router, "_check_database", ok)
    monkeypatch.setattr(health_router, "_check_qdrant", ok)
    monkeypatch.setattr(health_router, "_check_llm", ok)


# --------------------------------------------------------------------------- #
# AC4 — liveness
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_liveness_is_200_and_keeps_its_shape(client):
    """Formato estable: es lo que ya consumían compose y scripts."""
    async with client as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "alejandria_backend"}


@pytest.mark.asyncio
async def test_liveness_ignores_broken_dependencies(client, monkeypatch):
    """Lo importante de la distinción.

    Si el liveness mirase la base de datos, una caída de Postgres provocaría
    reinicios en bucle del backend sin arreglar nada y tirando las conexiones que
    sí funcionaban.
    """
    async def caido():
        raise AssertionError("el liveness no debe consultar dependencias")

    monkeypatch.setattr(health_router, "_check_database", caido)
    monkeypatch.setattr(health_router, "_check_qdrant", caido)
    monkeypatch.setattr(health_router, "_check_llm", caido)

    async with client as ac:
        response = await ac.get("/health")
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# AC4 — readiness
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_readiness_is_200_when_everything_answers(client, todo_ok):
    async with client as ac:
        response = await ac.get("/health/ready")

    assert response.status_code == 200
    cuerpo = response.json()
    assert cuerpo["status"] == "ready"
    assert set(cuerpo["checks"]) == {"database", "qdrant", "llm"}
    assert all(c["status"] == "ok" for c in cuerpo["checks"].values())


@pytest.mark.asyncio
@pytest.mark.parametrize("dependencia", ["_check_database", "_check_qdrant", "_check_llm"])
async def test_any_broken_dependency_returns_503_naming_it(client, todo_ok, monkeypatch, dependencia):
    async def roto():
        return "error", "no alcanzable"

    monkeypatch.setattr(health_router, dependencia, roto)

    async with client as ac:
        response = await ac.get("/health/ready")

    nombre = dependencia.replace("_check_", "")
    assert response.status_code == 503
    cuerpo = response.json()
    assert cuerpo["status"] == "not_ready"
    assert cuerpo["checks"][nombre]["status"] == "error"
    assert cuerpo["checks"][nombre]["reason"] == "no alcanzable"
    # Las sanas siguen reportándose: hace falta para saber qué NO es el problema.
    assert [c for n, c in cuerpo["checks"].items() if n != nombre and c["status"] == "ok"]


@pytest.mark.asyncio
async def test_readiness_reports_every_failure_not_just_the_first(client, monkeypatch):
    async def roto():
        return "error", "no alcanzable"

    async def ok():
        return "ok", None

    monkeypatch.setattr(health_router, "_check_database", roto)
    monkeypatch.setattr(health_router, "_check_qdrant", roto)
    monkeypatch.setattr(health_router, "_check_llm", ok)

    async with client as ac:
        cuerpo = (await ac.get("/health/ready")).json()

    fallando = [n for n, c in cuerpo["checks"].items() if c["status"] != "ok"]
    assert sorted(fallando) == ["database", "qdrant"]


@pytest.mark.asyncio
async def test_readiness_leaks_no_infrastructure_detail(client, monkeypatch):
    """Es público —lo consulta el orquestador—, así que no puede ser un mapa.

    Nada de URLs internas, credenciales ni mensajes del motor.
    """
    async def roto():
        return "error", "no alcanzable"

    monkeypatch.setattr(health_router, "_check_database", roto)
    monkeypatch.setattr(health_router, "_check_qdrant", roto)

    async with client as ac:
        texto = (await ac.get("/health/ready")).text

    for filtracion in ("postgres", "sqlite", "6333", "Traceback", "password", "api-key"):
        assert filtracion.lower() not in texto.lower(), f"readiness filtra {filtracion!r}"


@pytest.mark.asyncio
async def test_readiness_needs_no_authentication(client, todo_ok):
    """El orquestador no tiene credenciales; si exigiera token, nunca estaría sano."""
    async with client as ac:
        response = await ac.get("/health/ready")
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# AC4 — el chequeo de LLM sigue al proveedor configurado
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_a_remote_provider_without_a_key_is_not_ready(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "")
    estado, motivo = await health_router._check_llm()
    assert estado == "not_configured"
    assert motivo == "sin credencial"


@pytest.mark.asyncio
async def test_a_remote_provider_with_a_key_is_ready_without_calling_it(monkeypatch):
    """No se llama al proveedor: costaría dinero en cada sondeo, y son cada 15 s."""
    llamadas = []

    class _Prohibido:
        def __init__(self, *a, **k):
            llamadas.append(1)

    monkeypatch.setattr(settings, "LLM_PROVIDER", "anthropic")
    monkeypatch.setattr(settings, "ANTHROPIC_API_KEY", "SENTINEL-NO-USAR")
    monkeypatch.setattr(health_router.httpx, "AsyncClient", _Prohibido)

    estado, _ = await health_router._check_llm()
    assert estado == "ok"
    assert not llamadas, "se hizo una petición de red a un proveedor de pago"


@pytest.mark.asyncio
async def test_an_unknown_provider_is_reported_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "inventado")
    estado, _ = await health_router._check_llm()
    assert estado == "not_configured"


# --------------------------------------------------------------------------- #
# AC5 — el despliegue: límites y healthchecks
# --------------------------------------------------------------------------- #

def _compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("servicio", ["postgres", "qdrant", "ollama", "backend", "frontend"])
def test_every_service_declares_resource_limits(servicio):
    """Sin límites, un servicio que se desboca se lleva por delante a los demás."""
    limites = _compose()["services"][servicio].get("deploy", {}).get("resources", {}).get("limits", {})
    assert limites.get("cpus"), f"{servicio} sin límite de CPU"
    assert limites.get("memory"), f"{servicio} sin límite de memoria"


@pytest.mark.parametrize("servicio", ["postgres", "qdrant", "ollama", "backend", "frontend"])
def test_every_service_declares_a_healthcheck(servicio):
    assert _compose()["services"][servicio].get("healthcheck", {}).get("test"), (
        f"{servicio} sin healthcheck"
    )


def test_the_backend_healthcheck_probes_readiness_not_liveness():
    """AC5 pide readiness: un backend que vive pero no puede consultar la BD no está sano."""
    healthcheck = _compose()["services"]["backend"]["healthcheck"]
    assert "healthcheck.py" in " ".join(healthcheck["test"])
    assert healthcheck.get("start_period"), "sin start_period, el primer arranque se marca insano"


def test_the_backend_probe_script_exists_and_reports_readiness():
    """El script del healthcheck se prueba: uno averiado no avisa, solo deja de proteger."""
    from healthcheck import is_ready

    assert (ROOT_DIR / "healthcheck.py").exists()
    # Puerto cerrado → no listo, sin lanzar excepción.
    assert is_ready("http://127.0.0.1:9/health/ready", timeout=0.5) is False


def test_the_backend_waits_for_qdrant_to_be_healthy():
    """Tenía healthcheck pero se esperaba solo a que arrancara."""
    depends = _compose()["services"]["backend"]["depends_on"]
    assert depends["qdrant"]["condition"] == "service_healthy"


def test_the_llm_service_gets_the_largest_memory_budget():
    """Un modelo de 7B no cabe en el presupuesto de un servicio cualquiera."""
    servicios = _compose()["services"]

    def a_gib(valor: str) -> float:
        valor = str(valor).upper().rstrip("B")
        return float(valor[:-1]) / 1024 if valor.endswith("M") else float(valor[:-1])

    memorias = {
        n: a_gib(s["deploy"]["resources"]["limits"]["memory"]) for n, s in servicios.items()
    }
    assert memorias["ollama"] == max(memorias.values())
