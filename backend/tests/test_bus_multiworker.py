"""Coordinación entre workers (SPEC-018 / T4.3 / AC3).

AC3: con **más de un worker**, cuando un pipeline emite eventos SSE o espera una
decisión humana, streams/tareas/decisiones se coordinan vía Redis y **cualquier
worker puede atender la conexión, sin pérdida de eventos**.

Cada caso se ejecuta contra los **dos** backends: el bus en proceso —que es el que
usa el desarrollo y no puede romperse— y el de Redis. Los de Redis se **saltan**
solos si no hay servidor, para no teñir de rojo un CI que no levanta el servicio;
en este entorno se ejecutaron contra un Redis 7 real.

«Dos buses» equivale a dos workers: instancias separadas, con conexiones separadas,
sin nada en memoria en común. Es la única forma de probar de verdad que el estado
dejó de ser local.
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

import pytest
import pytest_asyncio

ROOT_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = ROOT_DIR.parent
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_bus.db").resolve()
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}")

from app.core.config import settings  # noqa: E402
from app.platform import bus as bus_module  # noqa: E402
from app.platform.bus import InProcessBus, RedisBus, get_bus, reset_bus  # noqa: E402

REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6399/0")
#: Margen para que un SUBSCRIBE llegue al servidor antes de publicar. Pub/sub no
#: guarda nada: quien no está suscrito cuando se publica, no lo recibe.
PROPAGACION = 0.3


async def _redis_disponible() -> bool:
    try:
        import redis.asyncio as aioredis

        cliente = aioredis.from_url(REDIS_URL)
        await asyncio.wait_for(cliente.ping(), timeout=1.0)
        await cliente.aclose()
        return True
    except Exception:
        return False


@pytest_asyncio.fixture(params=["memoria", "redis"])
async def dos_workers(request):
    """Dos buses independientes = dos workers."""
    if request.param == "redis":
        if not await _redis_disponible():
            pytest.skip(f"sin Redis en {REDIS_URL}")
        a, b = RedisBus(REDIS_URL), RedisBus(REDIS_URL)
    else:
        # En memoria, «dos workers» comparten instancia: es justo la limitación que
        # Redis viene a resolver, y así el mismo caso documenta ambos mundos.
        a = InProcessBus()
        b = a
    try:
        yield a, b
    finally:
        await a.close()
        if b is not a:
            await b.close()


# --------------------------------------------------------------------------- #
# AC3 — eventos: nadie se queda sin ellos
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_a_subscriber_on_another_worker_receives_the_event(dos_workers):
    """El caso que motiva la tarea: el pipeline corre en A, el navegador está en B."""
    a, b = dos_workers
    articulo = uuid.uuid4()

    async with b.subscribe(articulo) as cola:
        await asyncio.sleep(PROPAGACION)
        await a.publish(articulo, {"type": "token", "text": "hola"})
        evento = await asyncio.wait_for(cola.get(), 5)

    assert evento == {"type": "token", "text": "hola"}


@pytest.mark.asyncio
async def test_two_subscribers_get_the_same_events(dos_workers):
    """El test multi-worker que pide el plan de pruebas de la spec."""
    a, b = dos_workers
    articulo = uuid.uuid4()

    async with a.subscribe(articulo) as cola_a, b.subscribe(articulo) as cola_b:
        await asyncio.sleep(PROPAGACION)
        await a.publish(articulo, {"type": "agent_start", "agent": "redactor"})
        recibido_a = await asyncio.wait_for(cola_a.get(), 5)
        recibido_b = await asyncio.wait_for(cola_b.get(), 5)

    assert recibido_a == recibido_b == {"type": "agent_start", "agent": "redactor"}


@pytest.mark.asyncio
async def test_the_order_of_the_events_is_preserved(dos_workers):
    """Los `token` llegan barajados si cada publicación va en su propia tarea.

    Es peor que llegar tarde: el cliente compone el texto en el orden de llegada.
    """
    a, b = dos_workers
    articulo = uuid.uuid4()

    async with b.subscribe(articulo) as cola:
        await asyncio.sleep(PROPAGACION)
        for i in range(25):
            a.publish_nowait(articulo, {"type": "token", "i": i})   # sin await
        recibidos = [(await asyncio.wait_for(cola.get(), 5))["i"] for _ in range(25)]

    assert recibidos == list(range(25))


@pytest.mark.asyncio
async def test_events_for_another_article_are_not_delivered(dos_workers):
    a, b = dos_workers
    mio, ajeno = uuid.uuid4(), uuid.uuid4()

    async with b.subscribe(mio) as cola:
        await asyncio.sleep(PROPAGACION)
        await a.publish(ajeno, {"type": "token", "text": "de otro"})
        await a.publish(mio, {"type": "done"})
        evento = await asyncio.wait_for(cola.get(), 5)

    assert evento == {"type": "done"}, "llegó un evento de otro artículo"


@pytest.mark.asyncio
async def test_unsubscribing_stops_delivery(dos_workers):
    """Si la baja no funciona, cada cliente desconectado deja una fuga."""
    a, b = dos_workers
    articulo = uuid.uuid4()

    async with b.subscribe(articulo) as cola:
        await asyncio.sleep(PROPAGACION)
    await a.publish(articulo, {"type": "token"})
    await asyncio.sleep(PROPAGACION)

    assert cola.empty()


# --------------------------------------------------------------------------- #
# AC3 — presencia y cancelación
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_another_worker_sees_the_pipeline_as_running(dos_workers):
    """Sin esto, un `409 No active pipeline` sería mentira en cuanto haya 2 workers."""
    a, b = dos_workers
    articulo = uuid.uuid4()

    assert await b.is_running(articulo) is False
    await a.mark_running(articulo)
    assert await b.is_running(articulo) is True
    await a.clear_running(articulo)
    assert await b.is_running(articulo) is False


@pytest.mark.asyncio
async def test_cancelling_from_another_worker_reaches_the_task(dos_workers):
    """La tarea no viaja —es un `asyncio.Task`—, pero la señal sí."""
    a, b = dos_workers
    articulo = uuid.uuid4()
    cancelada = asyncio.Event()

    await a.mark_running(articulo)
    a.register_cancel_handler(articulo, cancelada.set)
    await asyncio.sleep(PROPAGACION)
    try:
        assert await b.request_cancel(articulo) is True
        await asyncio.wait_for(cancelada.wait(), 5)
    finally:
        a.unregister_cancel_handler(articulo)
        await a.clear_running(articulo)


@pytest.mark.asyncio
async def test_cancelling_something_that_is_not_running_says_so(dos_workers):
    _, b = dos_workers
    assert await b.request_cancel(uuid.uuid4()) is False


# --------------------------------------------------------------------------- #
# AC3 — decisión humana (HITL)
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_a_decision_submitted_on_another_worker_resumes_the_pipeline(dos_workers):
    """El pipeline espera en A; la petición HTTP con la decisión cae en B."""
    a, b = dos_workers
    articulo = uuid.uuid4()

    async def espera_en_a():
        async with a.awaiting_decision(articulo) as futuro:
            return await asyncio.wait_for(futuro, 10)

    esperando = asyncio.create_task(espera_en_a())
    await asyncio.sleep(PROPAGACION)
    try:
        assert await b.submit_decision(articulo, "add_source") is True
        assert await esperando == "add_source"
    finally:
        esperando.cancel()


@pytest.mark.asyncio
async def test_submitting_a_decision_nobody_awaits_returns_false(dos_workers):
    """Es lo que convierte el `409 No pending decision` en una respuesta honesta."""
    _, b = dos_workers
    assert await b.submit_decision(uuid.uuid4(), "continue") is False


@pytest.mark.asyncio
async def test_the_pending_mark_disappears_when_the_wait_ends(dos_workers):
    a, b = dos_workers
    articulo = uuid.uuid4()

    async with a.awaiting_decision(articulo):
        await asyncio.sleep(PROPAGACION)
        assert await b.submit_decision(articulo, "continue") is True

    await asyncio.sleep(PROPAGACION)
    assert await b.submit_decision(articulo, "continue") is False


# --------------------------------------------------------------------------- #
# AC3 — tickets de stream compartidos
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_a_ticket_issued_on_one_worker_is_valid_on_another(dos_workers):
    """El POST que emite el ticket y el SSE que lo canjea caen en workers distintos.

    Con el almacén local, el segundo respondería `403` sin motivo aparente.
    """
    a, b = dos_workers
    await a.store_ticket("tk-1", {"user_id": "u1", "article_id": "a1"}, 30)
    assert await b.take_ticket("tk-1") == {"user_id": "u1", "article_id": "a1"}


@pytest.mark.asyncio
async def test_a_ticket_is_single_use_across_workers(dos_workers):
    """Con `GETDEL` el canje es atómico: dos conexiones simultáneas no lo comparten."""
    a, b = dos_workers
    await a.store_ticket("tk-2", {"user_id": "u1", "article_id": "a1"}, 30)
    assert await b.take_ticket("tk-2") is not None
    assert await a.take_ticket("tk-2") is None


@pytest.mark.asyncio
async def test_an_unknown_ticket_is_rejected(dos_workers):
    _, b = dos_workers
    assert await b.take_ticket("no-existe") is None


# --------------------------------------------------------------------------- #
# Selección de backend y degradación
# --------------------------------------------------------------------------- #

@pytest.mark.asyncio
async def test_the_default_backend_is_in_process(monkeypatch):
    """Desarrollar no puede exigir levantar Redis."""
    monkeypatch.setattr(settings, "REDIS_ENABLED", False)
    await reset_bus()
    assert isinstance(get_bus(), InProcessBus)
    assert not isinstance(get_bus(), RedisBus)
    await reset_bus()


@pytest.mark.asyncio
async def test_enabling_redis_selects_the_redis_backend(monkeypatch):
    if not await _redis_disponible():
        pytest.skip(f"sin Redis en {REDIS_URL}")
    monkeypatch.setattr(settings, "REDIS_ENABLED", True)
    monkeypatch.setattr(settings, "REDIS_URL", REDIS_URL)
    await reset_bus()
    try:
        assert isinstance(get_bus(), RedisBus)
    finally:
        await reset_bus()


@pytest.mark.asyncio
async def test_a_broken_redis_degrades_instead_of_blocking_startup(monkeypatch):
    """Perder la coordinación degrada el servicio; no arrancar lo deja fuera del todo."""
    monkeypatch.setattr(settings, "REDIS_ENABLED", True)

    def _explota(url):
        raise RuntimeError("sin Redis")

    monkeypatch.setattr(bus_module, "RedisBus", _explota)
    await reset_bus()
    try:
        assert isinstance(get_bus(), InProcessBus)
    finally:
        monkeypatch.undo()
        await reset_bus()


# --------------------------------------------------------------------------- #
# Coherencia con el despliegue
# --------------------------------------------------------------------------- #

def _compose(nombre: str) -> dict:
    import yaml

    class T(yaml.SafeLoader):
        pass

    T.add_multi_constructor("!", lambda l, s, n: None)
    return yaml.load((REPO_DIR / nombre).read_text(encoding="utf-8"), Loader=T)


def test_the_compose_provides_a_redis_service():
    servicios = _compose("docker-compose.yml")["services"]
    assert "redis" in servicios
    assert servicios["redis"].get("healthcheck"), "sin healthcheck"
    assert not servicios["redis"].get("ports"), "Redis no debe publicarse al host"


def test_the_backend_waits_for_redis():
    depende = _compose("docker-compose.yml")["services"]["backend"]["depends_on"]
    assert depende["redis"]["condition"] == "service_healthy"


def test_production_turns_the_coordination_on():
    """Es donde hay varios workers; sin esto, el bus sería inútil justo ahí."""
    entorno = _compose("docker-compose.prod.yml")["services"]["backend"]["environment"]
    assert str(entorno["REDIS_ENABLED"]).lower() == "true"


def test_redis_is_a_declared_dependency():
    lock = (ROOT_DIR / "requirements.txt").read_text(encoding="utf-8")
    fuente = (ROOT_DIR / "requirements.in").read_text(encoding="utf-8")
    assert "redis" in fuente
    assert "\nredis==" in lock, "el lock no se recompiló tras añadir la dependencia"


def test_the_task_registry_is_documented_as_worker_local():
    """Es la limitación que hay que recordar: un `asyncio.Task` no se serializa."""
    fuente = (ROOT_DIR / "app/modules/agents/application/use_cases.py").read_text(encoding="utf-8")
    assert "local al worker" in fuente
