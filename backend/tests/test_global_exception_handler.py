"""Manejador global de excepciones (SPEC-016 / T2.4 / AC3 + AC4).

AC3: ante una excepción no controlada con ``DEBUG=false``, la respuesta ``500``
no expone traza ni detalles internos, y el error queda logueado con identificador
de correlación.

Se prueba sobre una app FastAPI mínima con el mismo cableado que ``app.main``
(``install_error_handling`` + middleware de correlación + CORS), en lugar de sobre
la app real: así los casos se centran en el manejador y no arrastran arranque de
BD, seeding ni routers. El orden de instalación es idéntico al de producción, que
es justo lo que estos tests deben proteger.
"""
import json
import logging
import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_errors.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from app.core import errors as errors_module  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.errors import GENERIC_ERROR_DETAIL, install_error_handling  # noqa: E402
from app.core.logging_config import (  # noqa: E402
    JsonFormatter,
    RequestIdFilter,
    request_id_middleware,
)

# Cadena que solo puede llegar al cliente si el detalle interno se filtra.
SECRET_IN_TRACEBACK = "detalle-interno-que-no-debe-salir"


class Boom(RuntimeError):
    """Excepción de prueba, no controlada por ningún router."""


def build_app() -> FastAPI:
    """App mínima con el mismo cableado (y orden) que ``app.main``."""
    app = FastAPI()
    install_error_handling(app)
    app.middleware("http")(request_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/boom")
    async def boom():
        raise Boom(SECRET_IN_TRACEBACK)

    @app.get("/boom-zero")
    async def boom_zero():
        return {"x": 1 / 0}

    @app.get("/not-found")
    async def not_found():
        raise HTTPException(status_code=404, detail="No existe")

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    return app


@pytest.fixture
def client():
    """Cliente que NO relanza la excepción, para observar la respuesta real."""
    app = build_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _production_mode(monkeypatch):
    """AC3 se enuncia con ``DEBUG=false``: ese es el modo por defecto aquí."""
    monkeypatch.setattr(settings, "DEBUG", False)


class _CapturingHandler(logging.Handler):
    """Handler que guarda los registros ya procesados por ``RequestIdFilter``.

    ``caplog`` no sirve aquí: su handler no lleva el filtro de T5.1, y aplicarlo a
    posteriori leería un ContextVar que la petición ya soltó. El id hay que
    observarlo tal como se estampa en el momento de emitir.
    """

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []
        self.addFilter(RequestIdFilter())

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def error_logs():
    """Registros emitidos por ``app.errors``, con el mismo filtro que en runtime."""
    handler = _CapturingHandler()
    logger = logging.getLogger("app.errors")
    logger.addHandler(handler)
    previous_propagate, logger.propagate = logger.propagate, False
    try:
        yield handler.records
    finally:
        logger.removeHandler(handler)
        logger.propagate = previous_propagate


# --------------------------------------------------------------------------- #
# AC3 — la respuesta no expone nada interno
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/boom", "/boom-zero"])
async def test_unhandled_exception_returns_500(client, path):
    async with client as ac:
        resp = await ac.get(path)
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_response_body_has_no_internal_detail(client):
    async with client as ac:
        resp = await ac.get("/boom")

    body = resp.text
    assert SECRET_IN_TRACEBACK not in body
    assert "Boom" not in body
    # Marcadores típicos de una traza de Python o de rutas del servidor.
    for leak in ("Traceback", "File \"", "app/core", "site-packages", ".py\", line"):
        assert leak not in body, f"la respuesta filtra {leak!r}"


@pytest.mark.asyncio
async def test_response_body_is_the_generic_payload(client):
    async with client as ac:
        resp = await ac.get("/boom")

    payload = resp.json()
    assert payload["detail"] == GENERIC_ERROR_DETAIL
    # En producción solo detail + request_id; nada de error_type ni traza.
    assert set(payload) == {"detail", "request_id"}


@pytest.mark.asyncio
async def test_error_type_is_exposed_only_in_debug(client, monkeypatch):
    monkeypatch.setattr(settings, "DEBUG", True)
    async with client as ac:
        resp = await ac.get("/boom")

    payload = resp.json()
    assert payload["error_type"] == "Boom"
    # Ni siquiera en debug viaja el *mensaje* de la excepción: puede llevar
    # credenciales o SQL. La traza completa vive en el log.
    assert SECRET_IN_TRACEBACK not in resp.text


# --------------------------------------------------------------------------- #
# AC3 — identificador de correlación en respuesta y log
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_response_carries_the_incoming_correlation_id(client):
    async with client as ac:
        resp = await ac.get("/boom", headers={"X-Request-ID": "corr-abc-123"})

    assert resp.json()["request_id"] == "corr-abc-123"
    assert resp.headers["X-Request-ID"] == "corr-abc-123"


@pytest.mark.asyncio
async def test_correlation_id_is_generated_when_absent(client):
    async with client as ac:
        resp = await ac.get("/boom")

    rid = resp.json()["request_id"]
    assert rid and rid != "-"
    assert resp.headers["X-Request-ID"] == rid


@pytest.mark.asyncio
async def test_error_is_logged_with_the_same_correlation_id(client, error_logs):
    async with client as ac:
        resp = await ac.get("/boom", headers={"X-Request-ID": "corr-log-9"})

    assert error_logs, "la excepción no se registró"
    # Sin este id compartido no se puede cruzar lo que ve el usuario con la traza.
    assert error_logs[0].request_id == resp.json()["request_id"] == "corr-log-9"


@pytest.mark.asyncio
async def test_log_keeps_the_full_traceback(client, error_logs):
    """Lo que se oculta al cliente tiene que seguir estando en el log."""
    async with client as ac:
        await ac.get("/boom")

    record = error_logs[0]
    assert record.exc_info is not None
    rendered = JsonFormatter().format(record)
    assert SECRET_IN_TRACEBACK in rendered
    assert "Traceback" in rendered


@pytest.mark.asyncio
async def test_log_record_has_contextual_fields(client, error_logs):
    async with client as ac:
        await ac.get("/boom")

    record = error_logs[0]
    assert record.event == "unhandled_exception"
    assert record.http_method == "GET"
    assert record.path == "/boom"
    assert record.exception_type == "Boom"

    payload = json.loads(JsonFormatter().format(record))
    assert payload["level"] == "ERROR"
    assert payload["path"] == "/boom"


# --------------------------------------------------------------------------- #
# No debe cambiar el resto del comportamiento
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_http_exceptions_are_not_swallowed(client):
    """404/4xx siguen siendo suyos: los resuelve ExceptionMiddleware, más interior."""
    async with client as ac:
        resp = await ac.get("/not-found")

    assert resp.status_code == 404
    assert resp.json() == {"detail": "No existe"}


@pytest.mark.asyncio
async def test_successful_requests_are_untouched(client):
    async with client as ac:
        resp = await ac.get("/ok")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_500_still_carries_cors_headers(client):
    """Sin CORS en el 500 el navegador ve un error de red y el id no llega nunca."""
    async with client as ac:
        resp = await ac.get("/boom", headers={"Origin": "http://localhost:5173"})

    assert resp.status_code == 500
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


# --------------------------------------------------------------------------- #
# Red de seguridad: el manejador registrado, fuera del middleware
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_registered_handler_covers_failures_outside_the_middleware():
    """Si estalla una capa *exterior* al middleware, el 500 sigue siendo opaco.

    Se simula con un middleware añadido después (y por tanto más al exterior) que
    revienta: el middleware de captura ni se ejecuta, y quien responde es el
    manejador de ``add_exception_handler``.
    """
    app = FastAPI()
    install_error_handling(app)
    app.middleware("http")(request_id_middleware)

    @app.middleware("http")
    async def explode_outside(request, call_next):
        raise Boom(SECRET_IN_TRACEBACK)

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/ok", headers={"X-Request-ID": "corr-outer"})

    assert resp.status_code == 500
    assert resp.json()["detail"] == GENERIC_ERROR_DETAIL
    assert SECRET_IN_TRACEBACK not in resp.text


@pytest.mark.asyncio
async def test_handler_falls_back_to_request_state_for_the_id():
    """Fuera del ContextVar el id se recupera de ``request.state``.

    Es el caso real del manejador registrado: corre por encima del middleware de
    correlación, que ya restableció el ContextVar.
    """
    app = FastAPI()
    install_error_handling(app)
    app.middleware("http")(request_id_middleware)

    @app.middleware("http")
    async def explode_outside(request, call_next):
        # Deja que el middleware interior fije state/ContextVar y falla al volver.
        await call_next(request)
        raise Boom("fallo posterior")

    @app.get("/ok")
    async def ok():
        return {"status": "ok"}

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/ok", headers={"X-Request-ID": "corr-state"})

    assert resp.status_code == 500
    assert resp.json()["request_id"] == "corr-state"


# --------------------------------------------------------------------------- #
# Cableado real
# --------------------------------------------------------------------------- #

def test_main_app_installs_the_handler():
    """La app real debe llevarlo puesto, no solo la app de prueba."""
    from app.main import app as real_app

    assert real_app.exception_handlers.get(Exception) is errors_module.unhandled_exception_handler
    names = [m.kwargs.get("dispatch").__name__ for m in real_app.user_middleware
             if m.kwargs.get("dispatch") is not None]
    assert "catch_unhandled_errors" in names


def test_catch_middleware_is_inside_cors_and_correlation():
    """El orden es la diferencia entre un 500 legible y un error de red opaco.

    ``user_middleware`` va de más exterior a más interior; el de captura tiene que
    ser el último (el más interior) de los tres.
    """
    from app.main import app as real_app

    labels = []
    for m in real_app.user_middleware:
        dispatch = m.kwargs.get("dispatch")
        labels.append(dispatch.__name__ if dispatch is not None else m.cls.__name__)

    assert labels.index("CORSMiddleware") < labels.index("request_id_middleware")
    assert labels.index("request_id_middleware") < labels.index("catch_unhandled_errors")
