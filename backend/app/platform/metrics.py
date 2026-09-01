"""Métricas Prometheus (SPEC-019 / T5.2 / AC2).

Expone en `/metrics`:

* **latencia y errores por endpoint** — con la *plantilla* de ruta, no la URL;
* **tokens y latencia de LLM por agente y modelo** — medidos donde de verdad se
  saben, que es dentro de cada proveedor.

**La cardinalidad es la decisión de diseño, no un detalle.** Una etiqueta con la
URL concreta (`/api/v1/articles/3f2a…/paper`) crea una serie temporal **por
artículo**: Prometheus las guarda todas, para siempre, y la instancia acaba
inservible por culpa de la instrumentación. Aquí se usa la plantilla de ruta
(`/api/v1/articles/{article_id}/paper`), que es un conjunto pequeño y fijo. Cuando
no se puede resolver —404, o una petición que no casó con ninguna ruta— se etiqueta
`unmatched` en lugar de dejar entrar la URL cruda.

**Varios workers.** `prometheus_client` guarda los contadores en memoria del
proceso, así que con varios workers cada uno reporta solo lo suyo. Definiendo
`PROMETHEUS_MULTIPROC_DIR` se agregan entre procesos; sin esa variable el módulo
funciona igual, pero conviene saber que lo que se ve es la parte de un worker.
"""
from __future__ import annotations

import logging
import os
import time
from contextvars import ContextVar
from typing import Optional

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest

logger = logging.getLogger(__name__)

#: Agente en ejecución, para etiquetar las llamadas al LLM sin arrastrar el nombre
#: por `call_llm` → `_retry_async` → `_call_<proveedor>`. Lo fija el orquestador en
#: `make_node_wrapper`, el punto por el que pasan **todos** los agentes, así que un
#: agente nuevo queda etiquetado sin tocar nada. Mismo patrón que `request_id_ctx`.
current_agent_ctx: ContextVar[str] = ContextVar("current_agent", default="none")

#: Cubetas pensadas para lo que se mide: peticiones HTTP de milisegundos.
_HTTP_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
#: Y para llamadas a un LLM, que tardan segundos o minutos. Reusar las de HTTP
#: dejaría casi todo en el cubo `+Inf` y los cuantiles no dirían nada.
_LLM_BUCKETS = (0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)

REGISTRY = CollectorRegistry()

http_requests_total = Counter(
    "http_requests_total",
    "Peticiones HTTP atendidas.",
    ["method", "route", "status"],
    registry=REGISTRY,
)
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Latencia de las peticiones HTTP.",
    ["method", "route"],
    buckets=_HTTP_BUCKETS,
    registry=REGISTRY,
)
llm_requests_total = Counter(
    "llm_requests_total",
    "Llamadas al proveedor de LLM.",
    ["provider", "model", "agent", "status"],
    registry=REGISTRY,
)
llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "Latencia de las llamadas al proveedor de LLM.",
    ["provider", "model", "agent"],
    buckets=_LLM_BUCKETS,
    registry=REGISTRY,
)
llm_tokens_total = Counter(
    "llm_tokens_total",
    "Tokens consumidos, por dirección (input/output).",
    ["provider", "model", "agent", "direction"],
    registry=REGISTRY,
)
agent_run_duration_seconds = Histogram(
    "agent_run_duration_seconds",
    "Duración de cada agente del pipeline.",
    ["agent", "status"],
    buckets=_LLM_BUCKETS,
    registry=REGISTRY,
)


def route_label(request, response=None) -> str:
    """Plantilla de ruta de la petición, nunca la URL concreta.

    Starlette deja la ruta que casó en `scope["route"]` **después** de enrutar, así
    que esto solo es fiable una vez atendida la petición.
    """
    ruta = request.scope.get("route")
    plantilla = getattr(ruta, "path", None)
    if plantilla:
        return plantilla
    # Sin ruta: 404, o un error antes de enrutar. Devolver `request.url.path` aquí
    # sería justo el fallo de cardinalidad que este módulo evita.
    return "unmatched"


def observe_llm_call(
    *,
    provider: str,
    model: str,
    duration: float,
    status: str,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    agent: Optional[str] = None,
) -> None:
    """Registrar una llamada al LLM. Nunca lanza: medir no puede romper el pipeline."""
    try:
        etiqueta_agente = agent or current_agent_ctx.get()
        llm_requests_total.labels(provider, model, etiqueta_agente, status).inc()
        llm_request_duration_seconds.labels(provider, model, etiqueta_agente).observe(duration)
        for direccion, cantidad in (("input", input_tokens), ("output", output_tokens)):
            if cantidad:
                llm_tokens_total.labels(provider, model, etiqueta_agente, direccion).inc(cantidad)
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudo registrar la métrica de LLM", exc_info=True)


def observe_llm_tokens(
    *, provider: str, model: str, input_tokens=None, output_tokens=None, agent=None
) -> None:
    """Solo tokens.

    Separada de `observe_llm_call` a propósito: los tokens se conocen dentro del
    proveedor y la duración fuera, y si ambos incrementaran `llm_requests_total`
    cada llamada se contaría dos veces.
    """
    try:
        etiqueta_agente = agent or current_agent_ctx.get()
        for direccion, cantidad in (("input", input_tokens), ("output", output_tokens)):
            if cantidad:
                llm_tokens_total.labels(provider, model, etiqueta_agente, direccion).inc(int(cantidad))
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudo registrar el consumo de tokens", exc_info=True)


def observe_agent_run(agent: str, duration: float, status: str) -> None:
    """Duración de un agente del pipeline. Tampoco lanza."""
    try:
        agent_run_duration_seconds.labels(agent, status).observe(duration)
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudo registrar la métrica del agente", exc_info=True)


async def metrics_middleware(request, call_next):
    """Cuenta y cronometra cada petición HTTP.

    El cronómetro se para en `finally` para que una excepción cuente igual: si solo
    se midieran las respuestas correctas, la latencia parecería mejorar justo
    cuando el servicio empieza a fallar.
    """
    inicio = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        duracion = time.perf_counter() - inicio
        ruta = route_label(request)
        if ruta != _METRICS_PATH:  # no medirse a sí mismo
            with_labels = http_request_duration_seconds.labels(request.method, ruta)
            with_labels.observe(duracion)
            http_requests_total.labels(request.method, ruta, status).inc()


_METRICS_PATH = "/metrics"


def render_metrics() -> tuple[bytes, str]:
    """Volcado en formato de exposición Prometheus.

    Con `PROMETHEUS_MULTIPROC_DIR` se agregan los contadores de todos los workers;
    sin ella, se reporta lo de este proceso.
    """
    directorio = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if directorio:
        try:
            from prometheus_client import multiprocess

            registro = CollectorRegistry()
            multiprocess.MultiProcessCollector(registro)
            return generate_latest(registro), CONTENT_TYPE_LATEST
        except Exception:
            logger.warning(
                "No se pudo agregar métricas entre procesos; se reporta solo este worker",
                exc_info=True,
                extra={"event": "metrics_multiproc_failed"},
            )
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST
