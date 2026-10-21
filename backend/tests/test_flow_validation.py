"""BUG-001 — un agente no puede conectarse consigo mismo.

La validación del navegador se salta con un `PUT /flows`, así que la que manda es
la del backend: guardar un flujo con una arista `source == target` se rechaza con
422 y los problemas estructurados (regla, nodos y aristas implicados).
"""
import os
import tempfile
from pathlib import Path
from uuid import uuid4

os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///" + (Path(tempfile.gettempdir()) / f"flow-validation-{os.getpid()}.db").as_posix()
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.platform.flow_validation import SELF_LOOP, blocking, validate_flow  # noqa: E402
from app.routers.auth import get_current_user  # noqa: E402

NODOS = [{"id": "a", "data": {"agentId": "redactor"}}, {"id": "b", "data": {"agentId": "revisor"}}]


# ─── Unitarias ─────────────────────────────────────────────────────────────────

def test_arista_a_si_mismo_es_invalida():
    issues = validate_flow(NODOS, [{"id": "e1", "source": "a", "target": "a"}])
    assert [i.code for i in issues] == [SELF_LOOP]
    assert issues[0].nodes == ("a",) and issues[0].edges == ("e1",)
    assert blocking(issues) == issues


def test_aristas_entre_nodos_distintos_son_validas():
    assert validate_flow(NODOS, [{"id": "e1", "source": "a", "target": "b"}]) == []


def test_aristas_malformadas_no_revientan():
    assert validate_flow(NODOS, [None, "x", {}]) == []


# ─── Integración ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": str(uuid4()), "role": "admin"}
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        await engine.dispose()


def _flow(edges):
    return {"name": "f", "nodes": NODOS, "edges": edges, "flow_sequence": ["redactor", "revisor"]}


@pytest.mark.asyncio
async def test_guardar_con_autoconexion_se_rechaza(client):
    resp = await client.post("/api/v1/flows", json=_flow([{"id": "e1", "source": "a", "target": "a"}]))
    assert resp.status_code == 422, resp.text
    issues = resp.json()["detail"]["issues"]
    assert issues[0]["code"] == SELF_LOOP and issues[0]["nodes"] == ["a"]


@pytest.mark.asyncio
async def test_actualizar_con_autoconexion_se_rechaza_y_lo_guardado_no_cambia(client):
    creado = await client.post("/api/v1/flows", json=_flow([{"id": "e1", "source": "a", "target": "b"}]))
    assert creado.status_code == 201, creado.text
    flow_id = creado.json()["id"]

    malo = await client.put(f"/api/v1/flows/{flow_id}", json={"edges": [{"id": "e2", "source": "b", "target": "b"}]})
    assert malo.status_code == 422, malo.text

    guardado = await client.get(f"/api/v1/flows/{flow_id}")
    assert guardado.json()["edges"] == [{"id": "e1", "source": "a", "target": "b"}]


@pytest.mark.asyncio
async def test_flujo_valido_sigue_guardandose(client):
    resp = await client.post("/api/v1/flows", json=_flow([{"id": "e1", "source": "a", "target": "b"}]))
    assert resp.status_code == 201, resp.text
