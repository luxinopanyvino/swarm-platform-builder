"""Manejo global de excepciones no controladas (SPEC-016 / T2.4 / AC3).

Sin un manejador global, una excepción que escapa de un router llega a
``ServerErrorMiddleware`` de Starlette y el cliente recibe un ``500`` cuyo cuerpo
depende del modo debug del servidor — en el peor caso, una traza completa con
rutas del sistema de ficheros, fragmentos de SQL o valores de configuración.

Aquí la respuesta es siempre **opaca y estable** (``detail`` genérico) y el
diagnóstico vive donde corresponde: en el log estructurado (SPEC-019 / T5.1),
con ``exc_info`` completo y el mismo ``request_id`` que se devuelve al cliente.
Así el usuario puede citar un identificador y soporte encuentra la traza exacta
sin que el detalle interno haya viajado nunca por la red.

Se instala en dos capas complementarias (:func:`install_error_handling`):

1. **Middleware** ``catch_unhandled_errors`` — la ruta normal. Se añade *dentro*
   de CORS, así que el ``500`` conserva las cabeceras CORS y el frontend puede
   leer el cuerpo (y el ``request_id``) en lugar de ver un error de red opaco.
2. **``app.add_exception_handler(Exception, …)``** — red de seguridad para lo que
   estalle *fuera* del middleware (en CORS, o en el propio middleware de
   correlación). Nunca se ejecutan los dos para la misma excepción: si el
   middleware responde, no se propaga nada hacia arriba.

Las ``HTTPException`` no pasan por aquí: las resuelve ``ExceptionMiddleware``,
que es interior a estas dos capas.
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.core.logging_config import request_id_ctx

logger = logging.getLogger("app.errors")

#: Cuerpo visible para el cliente. Deliberadamente sin detalle interno.
GENERIC_ERROR_DETAIL = "Error interno del servidor. Contacta con soporte citando el identificador."


def _correlation_id(request: Request) -> str:
    """Identificador de correlación de la petición actual.

    Prefiere el ``ContextVar`` (activo mientras el middleware de T5.1 envuelve la
    petición) y cae a ``request.state``, que sobrevive aunque el ``ContextVar`` ya
    se haya restablecido — el caso del manejador registrado, que corre por encima
    del middleware de correlación.
    """
    rid = request_id_ctx.get()
    if rid and rid != "-":
        return rid
    return getattr(request.state, "request_id", "-") or "-"


def build_error_response(request: Request, exc: Exception) -> JSONResponse:
    """Registra la excepción y construye el ``500`` opaco.

    El log lleva ``exc_info`` (traza completa) y campos contextuales — método,
    ruta y ``request_id`` — para poder cruzar el identificador que ve el usuario
    con la traza del servidor.
    """
    from app.core.config import settings  # perezoso: la config se recarga en caliente

    rid = _correlation_id(request)
    # Volvemos a fijar el ContextVar para que el filtro de T5.1 estampe el mismo
    # id en este registro aunque el middleware de correlación ya lo haya soltado.
    token = request_id_ctx.set(rid)
    try:
        logger.error(
            "Excepción no controlada en %s %s",
            request.method,
            request.url.path,
            exc_info=exc,
            extra={
                "event": "unhandled_exception",
                "http_method": request.method,
                "path": request.url.path,
                "exception_type": type(exc).__name__,
            },
        )
    finally:
        request_id_ctx.reset(token)

    payload: dict[str, str] = {"detail": GENERIC_ERROR_DETAIL, "request_id": rid}
    if settings.DEBUG:
        # Solo la *clase* de la excepción: orienta al desarrollador sin arrastrar
        # el mensaje, que puede contener credenciales o SQL. La traza está en el log.
        payload["error_type"] = type(exc).__name__

    return JSONResponse(status_code=500, content=payload, headers={"X-Request-ID": rid})


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Manejador registrado en ``add_exception_handler(Exception, …)``."""
    return build_error_response(request, exc)


async def catch_unhandled_errors(request: Request, call_next):
    """Middleware: convierte cualquier excepción escapada en el ``500`` opaco.

    Solo cubre el arranque de la respuesta. Si la excepción ocurre *mientras* se
    emite el cuerpo (SSE, streaming), ``call_next`` ya devolvió y las cabeceras ya
    salieron: no hay respuesta que sustituir, y el fallo lo gestiona el propio
    generador del stream.
    """
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - ese es exactamente el objetivo
        return build_error_response(request, exc)


def install_error_handling(app: FastAPI) -> None:
    """Instala el middleware y el manejador global.

    Debe invocarse **antes** de añadir CORS: en Starlette el middleware añadido
    más tarde queda más al exterior, así que llamar aquí primero deja este
    middleware por dentro de CORS (respuesta con cabeceras CORS) y por dentro del
    middleware de correlación (``request_id`` ya fijado).
    """
    app.middleware("http")(catch_unhandled_errors)
    app.add_exception_handler(Exception, unhandled_exception_handler)
