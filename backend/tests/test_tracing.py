"""Tracing OpenTelemetry (SPEC-019 / T5.3 / AC3).

AC3: con el tracing habilitado, **cada petición y cada paso de agente** generan
spans **anidados** exportables por OTLP; **activable por configuración y apagado
por defecto**.

Los spans se capturan con `InMemorySpanExporter`, así que se comprueba el árbol de
verdad —padres, hijos y atributos— en lugar de dar por bueno que se llamó a la
librería.
"""
import os
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_tracing.db").resolve()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}")

from app.core.config import Settings, settings  # noqa: E402
from app.core.logging_config import request_id_ctx  # noqa: E402
from app.platform import tracing  # noqa: E402


@pytest.fixture
def spans(monkeypatch):
    """Tracing encendido, exportando a memoria. Devuelve los spans terminados.

    El tracer sale de un proveedor **local**, no del global: OpenTelemetry solo
    deja fijar el global una vez por proceso (`Overriding of current
    TracerProvider is not allowed`), así que a partir del segundo test los spans
    se irían al exportador del primero y los casos se contaminarían entre sí.
    """
    # Importar la app **antes** de parchear: su import ejecuta `setup_tracing()`,
    # que deja `_tracer` a None y borraría el parche si llegara después.
    import app.main  # noqa: F401

    exportador = InMemorySpanExporter()
    proveedor = TracerProvider(resource=Resource.create({"service.name": "prueba"}))
    proveedor.add_span_processor(SimpleSpanProcessor(exportador))
    monkeypatch.setattr(tracing, "_tracer", proveedor.get_tracer("prueba"))
    try:
        yield exportador
    finally:
        tracing.reset_tracing()


def _por_nombre(exportador, nombre):
    return [s for s in exportador.get_finished_spans() if s.name == nombre]


# --------------------------------------------------------------------------- #
# AC3 — apagado por defecto
# --------------------------------------------------------------------------- #

def test_tracing_is_off_by_default():
    """Exporta a un colector externo: no puede encenderse por accidente."""
    assert Settings().OTEL_ENABLED is False


def test_setup_does_nothing_when_disabled(monkeypatch):
    monkeypatch.setattr(settings, "OTEL_ENABLED", False)
    tracing.reset_tracing()
    assert tracing.setup_tracing() is False
    assert tracing.is_enabled() is False


def test_spans_are_a_no_op_when_disabled(monkeypatch):
    """Los sitios instrumentados no comprueban nada: el módulo se encarga."""
    monkeypatch.setattr(tracing, "_tracer", None)
    with tracing.span("lo-que-sea", foo="bar") as actual:
        assert actual is None
    tracing.record_error(None, RuntimeError("x"))  # no debe lanzar


def test_a_broken_setup_degrades_instead_of_blocking_startup(monkeypatch):
    """Perder observabilidad degrada el diagnóstico; no arrancar deja el servicio fuera."""
    monkeypatch.setattr(settings, "OTEL_ENABLED", True)
    monkeypatch.setattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "no-es-una-url://")

    def _explota(*a, **k):
        raise RuntimeError("colector inalcanzable")

    monkeypatch.setattr("opentelemetry.sdk.trace.TracerProvider", _explota)
    tracing.reset_tracing()
    assert tracing.setup_tracing() is False   # avisa y sigue
    assert tracing.is_enabled() is False


# --------------------------------------------------------------------------- #
# AC3 — spans anidados por paso de agente
# --------------------------------------------------------------------------- #

def test_agent_spans_hang_from_the_pipeline_span(spans):
    """El árbol es lo que responde «¿dónde se fue el tiempo?»."""
    with tracing.span("pipeline.run", **{"article.id": "abc"}):
        for agente in ("investigador", "redactor"):
            with tracing.span(f"agent.{agente}", **{"agent.name": agente}):
                pass

    raiz = _por_nombre(spans, "pipeline.run")[0]
    hijos = [
        s for s in spans.get_finished_spans()
        if s.parent and s.parent.span_id == raiz.context.span_id
    ]
    assert sorted(s.name for s in hijos) == ["agent.investigador", "agent.redactor"]


def test_every_span_of_a_run_shares_one_trace(spans):
    with tracing.span("pipeline.run"):
        with tracing.span("agent.redactor"):
            pass

    trazas = {s.context.trace_id for s in spans.get_finished_spans()}
    assert len(trazas) == 1, "los pasos quedaron en trazas distintas"


def test_span_attributes_are_recorded(spans):
    with tracing.span("agent.redactor", **{"agent.name": "redactor", "article.id": "abc"}):
        pass

    atributos = _por_nombre(spans, "agent.redactor")[0].attributes
    assert atributos["agent.name"] == "redactor"
    assert atributos["article.id"] == "abc"


def test_none_attributes_are_omitted_not_stringified(spans):
    """`"None"` como valor de atributo es ruido que ensucia las búsquedas."""
    with tracing.span("agent.x", presente="sí", ausente=None):
        pass

    atributos = _por_nombre(spans, "agent.x")[0].attributes
    assert "presente" in atributos
    assert "ausente" not in atributos


def test_a_failed_step_is_marked_as_error(spans):
    """Un span sin marcar sale verde y la traza mentiría sobre lo que pasó."""
    from opentelemetry.trace import StatusCode

    with tracing.span("agent.redactor") as actual:
        tracing.record_error(actual, RuntimeError("fallo simulado"))

    span_agente = _por_nombre(spans, "agent.redactor")[0]
    assert span_agente.status.status_code == StatusCode.ERROR
    assert any(e.name == "exception" for e in span_agente.events)


# --------------------------------------------------------------------------- #
# AC3 — correlación con los logs de T5.1
# --------------------------------------------------------------------------- #

def test_spans_carry_the_request_id(spans):
    """Es lo que permite saltar de una traza al log exacto, y al revés."""
    token = request_id_ctx.set("corr-traza-1")
    try:
        with tracing.span("http.request"):
            pass
    finally:
        request_id_ctx.reset(token)

    assert _por_nombre(spans, "http.request")[0].attributes["request_id"] == "corr-traza-1"


def test_without_a_request_id_the_attribute_is_absent(spans):
    with tracing.span("pipeline.run"):
        pass
    assert "request_id" not in _por_nombre(spans, "pipeline.run")[0].attributes


# --------------------------------------------------------------------------- #
# AC3 — un span por petición
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_each_request_produces_a_span(spans):
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        await ac.get("/health")

    peticiones = [s for s in spans.get_finished_spans() if s.name.startswith("GET ")]
    assert peticiones, [s.name for s in spans.get_finished_spans()]
    assert peticiones[0].attributes["http.status_code"] == 200


@pytest.mark.asyncio
async def test_the_request_span_is_named_by_route_template(spans):
    """Igual que en las métricas: un nombre por artículo haría ilegible el visor."""
    import uuid

    from app.main import app

    articulo = uuid.uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        await ac.get(f"/api/v1/articles/{articulo}")

    nombres = [s.name for s in spans.get_finished_spans()]
    assert not any(str(articulo) in n for n in nombres), nombres
    assert any("{article_id}" in n for n in nombres), nombres


# --------------------------------------------------------------------------- #
# Configuración y despliegue
# --------------------------------------------------------------------------- #

def test_the_settings_use_the_standard_otel_names():
    """Quien ya opera un colector reconoce estas variables sin traducir nada."""
    for nombre in ("OTEL_ENABLED", "OTEL_SERVICE_NAME", "OTEL_EXPORTER_OTLP_ENDPOINT"):
        assert hasattr(settings, nombre)


def test_enabling_without_an_endpoint_is_warned_about(monkeypatch, caplog):
    """Generar spans que no van a ningún sitio es un fallo silencioso de configuración."""
    import logging

    monkeypatch.setattr(settings, "OTEL_ENABLED", True)
    monkeypatch.setattr(settings, "OTEL_EXPORTER_OTLP_ENDPOINT", "")
    tracing.reset_tracing()
    with caplog.at_level(logging.WARNING):
        activo = tracing.setup_tracing()
    tracing.reset_tracing()

    assert activo is True, "sin endpoint debe seguir trazando en local"
    assert any("sin OTEL_EXPORTER_OTLP_ENDPOINT" in r.getMessage() for r in caplog.records)


def test_the_dependencies_are_pinned():
    lock = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8")
    assert "\nopentelemetry-sdk==" in lock
    assert "\nopentelemetry-exporter-otlp-proto-http==" in lock


def test_the_shipped_config_keeps_tracing_off():
    import yaml

    for ruta in ("config.yaml", "backend/config.yaml"):
        datos = yaml.safe_load((ROOT_DIR.parent / ruta).read_text(encoding="utf-8"))
        assert datos.get("otel", {}).get("enabled") is False, ruta
