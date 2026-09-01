"""Tracing OpenTelemetry (SPEC-019 / T5.3 / AC3).

AC3: con el tracing habilitado, **cada petición y cada paso de agente** generan
spans anidados exportables por OTLP; **apagado por defecto**.

Lo que aporta sobre lo que ya hay: los logs de T5.1 cuentan *qué* pasó y las
métricas de T5.2 *cuánto*, pero ninguno de los dos dice **dónde se fue el tiempo**
dentro de una ejecución. Una traza sí: enseña el árbol
`pipeline → investigador → redactor → …` con la duración de cada rama, que es la
pregunta real cuando una generación tarda ocho minutos.

**Apagado significa apagado.** Sin `OTEL_ENABLED` no se importa el SDK, no se
crean spans y las funciones de este módulo son envoltorios vacíos: el coste es una
comprobación booleana. Es deliberado — el tracing exporta a un colector externo y
no debe encenderse por accidente.

**Se integra con lo que ya existe** en vez de duplicarlo: cada span lleva el
`request_id` de T5.1 como atributo, así que desde una traza se llega al log exacto
y desde un log a su traza.
"""
from __future__ import annotations

import contextlib
import logging
from typing import Any, Iterator, Optional

from app.core.config import settings
from app.core.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

_tracer: Optional[Any] = None
_initialised = False


def _resource_attributes() -> dict:
    return {"service.name": settings.OTEL_SERVICE_NAME or "alejandria-backend"}


def setup_tracing() -> bool:
    """Preparar el proveedor de trazas. Devuelve si quedó activo.

    Se llama una vez al arrancar. Si el SDK no está instalado o el colector no se
    puede configurar, **se avisa y se sigue sin tracing**: perder observabilidad
    degrada el diagnóstico, no arrancar deja el servicio fuera.
    """
    global _tracer, _initialised
    _initialised = True

    if not settings.OTEL_ENABLED:
        _tracer = None
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create(_resource_attributes()))

        endpoint = settings.OTEL_EXPORTER_OTLP_ENDPOINT
        if endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            # BatchSpanProcessor y no Simple: exporta en lotes y en segundo plano.
            # El simple bloquea la petición hasta que el colector responde, así que
            # un colector lento se convertiría en latencia del usuario.
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        else:
            logger.warning(
                "Tracing activado sin OTEL_EXPORTER_OTLP_ENDPOINT: se generan spans "
                "pero no se exportan a ningún sitio.",
                extra={"event": "tracing_without_exporter"},
            )

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("alejandria")
        logger.info(
            "Tracing OpenTelemetry activo",
            extra={"event": "tracing_enabled", "endpoint": endpoint or "sin exportador"},
        )
        return True
    except Exception:
        logger.error(
            "No se pudo inicializar el tracing; se continúa sin él.",
            exc_info=True,
            extra={"event": "tracing_setup_failed"},
        )
        _tracer = None
        return False


def is_enabled() -> bool:
    return _tracer is not None


def reset_tracing() -> None:
    """Soltar el proveedor (tests)."""
    global _tracer, _initialised
    _tracer = None
    _initialised = False


@contextlib.contextmanager
def span(name: str, **attributes: Any) -> Iterator[Any]:
    """Abrir un span, o no hacer nada si el tracing está apagado.

    Con el tracing apagado esto es un `yield None`: los sitios instrumentados no
    necesitan comprobar nada y el código queda igual de legible en ambos casos.
    """
    if _tracer is None:
        yield None
        return

    with _tracer.start_as_current_span(name) as actual:
        try:
            # El id de correlación de T5.1 en cada span: es lo que une traza y log.
            correlacion = request_id_ctx.get()
            if correlacion and correlacion != "-":
                actual.set_attribute("request_id", correlacion)
            for clave, valor in attributes.items():
                if valor is not None:
                    actual.set_attribute(clave, str(valor))
        except Exception:  # pragma: no cover - defensivo
            pass
        yield actual


def record_error(actual_span: Any, exc: BaseException) -> None:
    """Marcar el span como fallido. Sin span (tracing apagado) no hace nada."""
    if actual_span is None:
        return
    with contextlib.suppress(Exception):
        from opentelemetry.trace import Status, StatusCode

        actual_span.record_exception(exc)
        actual_span.set_status(Status(StatusCode.ERROR, str(exc)))


async def tracing_middleware(request, call_next):
    """Un span por petición HTTP.

    El nombre usa la **plantilla** de ruta, no la URL: igual que en las métricas,
    un nombre por artículo haría ilegible cualquier agrupación en el visor de
    trazas.
    """
    if _tracer is None:
        return await call_next(request)

    with span("http.request", **{"http.method": request.method}) as actual:
        try:
            response = await call_next(request)
        except Exception as exc:
            record_error(actual, exc)
            raise
        if actual is not None:
            with contextlib.suppress(Exception):
                from app.platform.metrics import route_label

                actual.update_name(f"{request.method} {route_label(request)}")
                actual.set_attribute("http.route", route_label(request))
                actual.set_attribute("http.status_code", response.status_code)
        return response
