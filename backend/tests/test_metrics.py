"""Métricas Prometheus (SPEC-019 / T5.2 / AC2).

AC2: `/metrics` expone en formato Prometheus **latencia y errores por endpoint** y
**contadores de tokens/latencia de LLM por agente y modelo**.

El caso al que hay que prestar atención es el de cardinalidad. Una etiqueta con la
URL concreta crea una serie temporal por artículo y acaba inutilizando la instancia
de Prometheus: el fallo no aparece en desarrollo —donde hay tres artículos— sino
meses después, en producción. Por eso hay varios casos dedicados a que la etiqueta
sea la **plantilla** de ruta.
"""
import os
import sys
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_metrics.db").resolve()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}")

from app.platform import metrics as metrics_module  # noqa: E402
from app.platform.metrics import (  # noqa: E402
    current_agent_ctx,
    observe_agent_run,
    observe_llm_call,
    observe_llm_tokens,
    render_metrics,
)


@pytest.fixture
def client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _volcado() -> str:
    cuerpo, _ = render_metrics()
    return cuerpo.decode()


def _series(nombre: str) -> list[str]:
    return [l for l in _volcado().splitlines() if l.startswith(nombre) and not l.startswith("#")]


# --------------------------------------------------------------------------- #
# AC2 — el endpoint
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_metrics_is_served_in_prometheus_format(client):
    async with client as ac:
        respuesta = await ac.get("/metrics")

    assert respuesta.status_code == 200
    assert "text/plain" in respuesta.headers["content-type"]
    # El formato de exposición lleva HELP y TYPE por métrica.
    assert "# HELP" in respuesta.text and "# TYPE" in respuesta.text


@pytest.mark.asyncio
async def test_metrics_needs_no_authentication(client):
    """El recolector no tiene credenciales; si las pidiera, no recogería nada."""
    async with client as ac:
        assert (await ac.get("/metrics")).status_code == 200


def test_metrics_is_not_exposed_through_the_public_gateway():
    """nginx solo hace de pasarela para `/api/` (T3.4), así que `/metrics` se queda
    en la red interna. Si algún día se publicara, habría que protegerlo."""
    for conf in ("nginx.conf", "nginx.prod.conf"):
        texto = (ROOT_DIR.parent / "frontend" / conf).read_text(encoding="utf-8")
        assert "/metrics" not in texto


# --------------------------------------------------------------------------- #
# AC2 — latencia y errores por endpoint
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_requests_are_counted_with_method_route_and_status(client):
    async with client as ac:
        await ac.get("/health")
        volcado = (await ac.get("/metrics")).text

    lineas = [l for l in volcado.splitlines() if l.startswith("http_requests_total")]
    assert any('method="GET"' in l and 'route="/health"' in l and 'status="200"' in l for l in lineas), lineas


@pytest.mark.asyncio
async def test_request_latency_is_observed(client):
    async with client as ac:
        await ac.get("/health")

    assert any('route="/health"' in l for l in _series("http_request_duration_seconds_count"))


@pytest.mark.asyncio
async def test_errors_are_counted_with_their_status(client):
    """«Errores por endpoint» sale de la etiqueta `status`, no de un contador aparte."""
    async with client as ac:
        await ac.get(f"/api/v1/articles/{uuid.uuid4()}")   # sin token → 401/403
        volcado = (await ac.get("/metrics")).text

    lineas = [l for l in volcado.splitlines() if l.startswith("http_requests_total")]
    assert any('status="4' in l for l in lineas), "no se contabilizó ninguna respuesta 4xx"


# --------------------------------------------------------------------------- #
# AC2 — cardinalidad: la etiqueta es la plantilla, nunca la URL
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_the_route_label_is_the_template_not_the_url(client):
    """Dos artículos distintos tienen que compartir serie temporal."""
    uno, dos = uuid.uuid4(), uuid.uuid4()
    async with client as ac:
        await ac.get(f"/api/v1/articles/{uno}")
        await ac.get(f"/api/v1/articles/{dos}")
        volcado = (await ac.get("/metrics")).text

    assert str(uno) not in volcado, "la URL concreta entró como etiqueta"
    assert str(dos) not in volcado
    assert "{article_id}" in volcado, "no se está usando la plantilla de ruta"


@pytest.mark.asyncio
async def test_an_unmatched_path_does_not_leak_into_a_label(client):
    """Un 404 no puede meter la URL inventada en una etiqueta: sería el vector más
    fácil para reventar la cardinalidad desde fuera."""
    basura = f"/no-existe/{uuid.uuid4()}"
    async with client as ac:
        await ac.get(basura)
        volcado = (await ac.get("/metrics")).text

    assert basura not in volcado
    assert 'route="unmatched"' in volcado


# --------------------------------------------------------------------------- #
# AC2 — LLM por agente y modelo
# --------------------------------------------------------------------------- #

def test_llm_latency_is_labelled_by_provider_model_and_agent():
    observe_llm_call(
        provider="anthropic", model="claude-opus-5", duration=2.5,
        status="ok", agent="redactor",
    )
    series = _series("llm_request_duration_seconds_count")
    assert any(
        'provider="anthropic"' in l and 'model="claude-opus-5"' in l and 'agent="redactor"' in l
        for l in series
    ), series


def test_llm_tokens_are_counted_by_direction():
    observe_llm_tokens(
        provider="ollama", model="mistral:7b", input_tokens=120, output_tokens=340,
        agent="investigador",
    )
    series = _series("llm_tokens_total")
    assert any('direction="input"' in l and l.strip().endswith("120.0") for l in series), series
    assert any('direction="output"' in l and l.strip().endswith("340.0") for l in series), series


def test_a_failed_call_is_counted_with_its_status():
    observe_llm_call(provider="openai", model="gpt-4o-mini", duration=0.4, status="error", agent="revisor")
    assert any('status="error"' in l for l in _series("llm_requests_total"))


def test_the_agent_label_comes_from_the_context_when_not_passed():
    """El orquestador lo fija una vez y el dispatcher no tiene que enterarse."""
    token = current_agent_ctx.set("formateador")
    try:
        observe_llm_call(provider="anthropic", model="claude-opus-5", duration=1.0, status="ok")
    finally:
        current_agent_ctx.reset(token)

    assert any('agent="formateador"' in l for l in _series("llm_requests_total"))


def test_without_an_agent_in_context_the_label_is_none_not_missing():
    """Una etiqueta ausente rompe las consultas; un valor explícito no."""
    observe_llm_call(provider="anthropic", model="claude-opus-5", duration=1.0, status="ok")
    assert any('agent="none"' in l for l in _series("llm_requests_total"))


def test_agent_runs_are_timed():
    observe_agent_run("publicador", 12.0, "completed")
    assert any('agent="publicador"' in l and 'status="completed"' in l
               for l in _series("agent_run_duration_seconds_count"))


def test_measuring_never_raises(monkeypatch):
    """Medir no puede tumbar el pipeline: si la métrica falla, se traga el error."""
    def _explota(*a, **k):
        raise RuntimeError("registro roto")

    monkeypatch.setattr(metrics_module.llm_requests_total, "labels", _explota)
    observe_llm_call(provider="x", model="y", duration=1.0, status="ok")   # no debe lanzar


# --------------------------------------------------------------------------- #
# Instrumentación del dispatcher
# --------------------------------------------------------------------------- #

def test_the_llm_dispatcher_reports_usage_where_the_provider_gives_it():
    """Los tokens se leen dentro del proveedor: es el único sitio donde se saben."""
    fuente = (ROOT_DIR / "app/platform/llm.py").read_text(encoding="utf-8")
    assert fuente.count("_record_usage(") >= 5, "faltan proveedores instrumentados"
    for proveedor in ('"ollama"', '"anthropic"', '"openai"'):
        assert f"_record_usage({proveedor}" in fuente


def test_the_openai_stream_gap_is_documented():
    """Lo que no se mide se dice, en vez de reportar ceros como si fueran reales."""
    fuente = (ROOT_DIR / "app/platform/llm.py").read_text(encoding="utf-8")
    assert "stream_options" in fuente and "pasarelas compatibles" in fuente


def test_llm_and_http_use_different_latency_buckets():
    """Reusar las de HTTP dejaría toda llamada a un LLM en el cubo `+Inf`."""
    assert max(metrics_module._LLM_BUCKETS) > max(metrics_module._HTTP_BUCKETS) * 10


def test_the_dependency_is_pinned():
    lock = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8")
    assert "\nprometheus-client==" in lock
