"""VAL-004 — orden lógico, ciclos y agentes huérfanos en el Flow Designer.

Las reglas de dependencia son datos de la plantilla del proyecto
(`graph.flow_rules`), no código: estos tests las leen de ahí.
"""
import os
import tempfile
from pathlib import Path
from uuid import uuid4

os.environ["DATABASE_URL"] = (
    "sqlite+aiosqlite:///" + (Path(tempfile.gettempdir()) / f"flow-rules-{os.getpid()}.db").as_posix()
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.agents.domain import alejandria  # noqa: E402
from app.platform.flow_validation import (  # noqa: E402
    CYCLE, MISSING_DEPENDENCY, NO_RULES, ORPHAN, WRONG_ORDER,
    blocking, effective_order, relax_dependencies, validate_flow, validate_sequence,
)
from app.routers.auth import get_current_user  # noqa: E402

REGLAS = alejandria.package().flow_rules


def _nodo(id_, agente):
    return {"id": id_, "data": {"agentId": agente}}


def _arista(origen, destino):
    return {"id": f"{origen}-{destino}", "source": origen, "target": destino}


def _codigos(issues):
    return sorted(i.code for i in issues)


def test_las_reglas_salen_de_la_plantilla_y_no_del_codigo():
    assert [(r.agent, r.severity) for r in REGLAS.requires] == [
        ("publicador", "error"), ("publicador", "warning"),
    ]


def test_publicador_antes_de_redactor_es_bloqueante_y_senala_la_arista():
    nodos = [_nodo("p", "publicador"), _nodo("r", "redactor")]
    issues = validate_flow(nodos, [_arista("p", "r")], REGLAS)
    wrong = [i for i in issues if i.code == WRONG_ORDER and i.severity == "error"]
    assert len(wrong) == 1
    assert wrong[0].message == "Publicador no puede ejecutarse antes de Redactor"
    assert wrong[0].edges == ("p-r",) and wrong[0].nodes == ("p", "r")


def test_publicador_sin_redactor_en_el_flujo_es_bloqueante():
    nodos = [_nodo("f", "formateador"), _nodo("p", "publicador")]
    issues = validate_flow(nodos, [_arista("f", "p")], REGLAS)
    assert MISSING_DEPENDENCY in _codigos(blocking(issues))


def test_publicador_sin_revisor_ni_formateador_es_solo_aviso():
    nodos = [_nodo("r", "redactor"), _nodo("p", "publicador")]
    issues = validate_flow(nodos, [_arista("r", "p")], REGLAS)
    assert blocking(issues) == []
    assert [(i.code, i.severity) for i in issues] == [(MISSING_DEPENDENCY, "warning")]


def test_flujo_editorial_completo_no_da_problemas():
    ids = ["investigador", "redactor", "revisor", "formateador", "publicador"]
    nodos = [_nodo(a, a) for a in ids]
    aristas = [_arista(a, b) for a, b in zip(ids, ids[1:])]
    assert validate_flow(nodos, aristas, REGLAS) == []


def test_sin_aristas_se_ejecuta_en_el_orden_del_lienzo():
    """El motor corre `flow_sequence`; un flujo sin conectar corre como se soltó."""
    nodos = [_nodo("p", "publicador"), _nodo("r", "redactor")]
    assert effective_order(nodos, []) == ["p", "r"]
    assert WRONG_ORDER in _codigos(validate_flow(nodos, [], REGLAS))


def test_las_aristas_mandan_sobre_el_orden_del_lienzo():
    nodos = [_nodo("p", "publicador"), _nodo("r", "redactor")]
    assert effective_order(nodos, [_arista("r", "p")]) == ["r", "p"]


@pytest.mark.parametrize("ids", [["a", "b"], ["a", "b", "c"]])
def test_ciclos_de_cualquier_longitud_son_bloqueantes(ids):
    nodos = [_nodo(i, f"ag_{i}") for i in ids]
    aristas = [_arista(a, b) for a, b in zip(ids, ids[1:])] + [_arista(ids[-1], ids[0])]
    ciclo = [i for i in validate_flow(nodos, aristas, NO_RULES) if i.code == CYCLE]
    assert len(ciclo) == 1 and ciclo[0].severity == "error"
    assert set(ciclo[0].nodes) == set(ids) and len(ciclo[0].edges) == len(ids)


def test_un_nodo_que_cuelga_de_un_ciclo_no_se_marca_como_parte_de_el():
    nodos = [_nodo(i, f"ag_{i}") for i in "abc"]
    aristas = [_arista("a", "b"), _arista("b", "a"), _arista("b", "c")]
    ciclo = [i for i in validate_flow(nodos, aristas, NO_RULES) if i.code == CYCLE][0]
    assert set(ciclo.nodes) == {"a", "b"}


def test_agente_sin_conexiones_es_aviso_solo_en_flujos_de_varios():
    nodos = [_nodo("r", "redactor"), _nodo("v", "revisor"), _nodo("x", "formateador")]
    issues = validate_flow(nodos, [_arista("r", "v")], REGLAS)
    huerfanos = [i for i in issues if i.code == ORPHAN]
    assert [(i.nodes, i.severity) for i in huerfanos] == [(("x",), "warning")]
    assert validate_flow([_nodo("r", "redactor")], [], REGLAS) == []


def test_validar_la_secuencia_que_se_ejecuta():
    assert blocking(validate_sequence(["publicador", "redactor"], REGLAS)) != []
    assert blocking(validate_sequence(["redactor", "revisor", "publicador"], REGLAS)) == []


def test_republicar_un_articulo_ya_redactado_no_exige_redactor():
    assert blocking(validate_sequence(["publicador"], REGLAS)) != []
    assert blocking(validate_sequence(["publicador"], REGLAS, existing_output=True)) == []


def test_modo_aviso_degrada_dependencias_pero_no_ciclos():
    nodos = [_nodo("p", "publicador"), _nodo("q", "x"), _nodo("y", "y")]
    issues = validate_flow(nodos, [_arista("q", "y"), _arista("y", "q")], REGLAS)
    relajado = relax_dependencies(issues)
    assert CYCLE in _codigos(blocking(relajado))
    assert not [i for i in blocking(relajado) if i.code in (WRONG_ORDER, MISSING_DEPENDENCY)]


# ─── Integración: el backend manda aunque se salten la interfaz ───────────────

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


def _flow(nodos, aristas, secuencia):
    return {"name": "f", "nodes": nodos, "edges": aristas, "flow_sequence": secuencia}


@pytest.mark.asyncio
async def test_el_backend_rechaza_publicador_antes_de_redactor(client):
    nodos = [_nodo("p", "publicador"), _nodo("r", "redactor")]
    resp = await client.post("/api/v1/flows", json=_flow(nodos, [_arista("p", "r")], ["publicador", "redactor"]))
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["issues"][0]["code"] == WRONG_ORDER


@pytest.mark.asyncio
async def test_el_backend_rechaza_un_ciclo(client):
    nodos = [_nodo("a", "redactor"), _nodo("b", "revisor")]
    aristas = [_arista("a", "b"), _arista("b", "a")]
    resp = await client.post("/api/v1/flows", json=_flow(nodos, aristas, ["redactor", "revisor"]))
    assert resp.status_code == 422 and resp.json()["detail"]["issues"][0]["code"] == CYCLE


@pytest.mark.asyncio
async def test_los_avisos_no_bloquean_el_guardado(client):
    nodos = [_nodo("r", "redactor"), _nodo("p", "publicador")]
    resp = await client.post("/api/v1/flows", json=_flow(nodos, [_arista("r", "p")], ["redactor", "publicador"]))
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_el_endpoint_de_reglas_sirve_las_de_la_plantilla(client):
    resp = await client.get("/api/v1/flows/rules")
    assert resp.status_code == 200 and resp.json() == REGLAS.as_dict()


@pytest.mark.asyncio
async def test_los_flujos_sembrados_siguen_siendo_validos(client):
    """Regresión: los pipelines que trae la siembra no pueden quedar bloqueados."""
    for secuencia in (
        ["investigador", "redactor", "revisor", "formateador", "publicador"],
        ["redactor", "revisor", "publicador"],
    ):
        nodos = [_nodo(a, a) for a in secuencia]
        aristas = [_arista(a, b) for a, b in zip(secuencia, secuencia[1:])]
        resp = await client.post("/api/v1/flows", json=_flow(nodos, aristas, secuencia))
        assert resp.status_code == 201, resp.text
