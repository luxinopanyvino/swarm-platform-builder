"""Endpoint de explicabilidad y su panel (SPEC-014 / T9.2 / AC2).

AC2: dado un artículo con ejecuciones, `GET /api/v1/agents/{article_id}/explain`
devuelve la traza completa estructurada, y la interfaz muestra un panel «Por qué
este resultado» con fuentes, score y decisiones por paso.

T9.1 dejó la traza escrita en `agent_run_steps`. Lo que falta —y es la parte que
puede salir mal sin que nadie lo note— es **leerla bien**: un artículo se puede
reejecutar, y entonces su traza tiene varias ejecuciones en la misma tabla.
Devolverlas mezcladas contaría una historia que no ocurrió, con el revisor
aprobando un borrador que ya no existe.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_explain_api.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    AgentRunStepModel, ArticleModel, ProjectModel, UserModel, UserRole,
)
from app.platform import explainability as ex  # noqa: E402


# ── Agrupar ejecuciones: funciones puras, sin base de datos ─────────────────

def _paso(step_index, agent="redactor", **campos):
    base = dict(
        step_index=step_index, agent_name=agent, iteration=0, status="completed",
        tokens_in=0, tokens_out=0, latency_ms=0.0, rag_sources=[],
    )
    base.update(campos)
    return SimpleNamespace(**base)


def test_dos_ejecuciones_no_se_mezclan_en_una():
    """El fallo que hace falso el panel: `step_index` vuelve a 0 en cada
    ejecución, así que ordenar por él entrelaza dos historias distintas."""
    pasos = [_paso(0), _paso(1), _paso(2), _paso(0), _paso(1)]
    ejecuciones = ex.group_executions(pasos)
    assert [len(e) for e in ejecuciones] == [3, 2]


def test_una_reanudacion_es_la_misma_ejecucion():
    """`resume` continúa desde el checkpoint y **no** reinicia `step_index`: es
    la misma ejecución terminada en un segundo intento, no una nueva."""
    pasos = [_paso(0), _paso(1, status="error"), _paso(2), _paso(3)]
    assert len(ex.group_executions(pasos)) == 1


def test_sin_pasos_no_hay_ejecuciones():
    assert ex.group_executions([]) == []


def test_las_fuentes_se_agregan_a_traves_de_los_pasos():
    """La pregunta del panel es «¿en qué documentos se apoya el artículo?», y la
    traza las guarda por paso. Agruparlo en cada cliente lo haría distinto."""
    pasos = [
        _paso(0, agent="investigador", rag_sources=[
            {"doc_id": "d1", "title": "Uno", "score": 0.7, "chunk_ids": [1]},
            {"doc_id": "d2", "score": 0.9, "chunk_ids": [5]},
        ]),
        _paso(1, agent="redactor", rag_sources=[
            {"doc_id": "d1", "score": 0.95, "chunk_ids": [2], "authors": "A"},
        ]),
    ]
    fuentes = {f["doc_id"]: f for f in ex.aggregate_sources(pasos)}

    # El mejor score de cualquier paso representa al documento.
    assert fuentes["d1"]["score"] == 0.95
    assert fuentes["d1"]["chunk_ids"] == [1, 2]
    # Los metadatos se completan con el primer paso que los traiga.
    assert fuentes["d1"]["title"] == "Uno" and fuentes["d1"]["authors"] == "A"
    # Y quién la usó: distingue lo que solo vio el investigador de lo que además
    # usó el redactor al ampliar el borrador.
    assert fuentes["d1"]["used_by"] == ["investigador", "redactor"]
    assert fuentes["d2"]["used_by"] == ["investigador"]

    # De mejor a peor: la fuente que más pesó, primero.
    assert [f["doc_id"] for f in ex.aggregate_sources(pasos)] == ["d1", "d2"]


def test_una_fuente_sin_doc_id_no_entra():
    """Se ignora en vez de crear una fila fantasma sin nada que enseñar."""
    pasos = [_paso(0, rag_sources=[{"score": 0.9}, "no soy un dict", {"doc_id": ""}])]
    assert ex.aggregate_sources(pasos) == []


def test_un_score_no_numerico_no_tumba_la_agregacion():
    """`rag_sources` es JSON: lo que haya escrito ahí una versión anterior o un
    backend distinto no puede reventar la lectura de toda la traza."""
    pasos = [_paso(0, rag_sources=[{"doc_id": "d1", "score": "alto"}])]
    assert ex.aggregate_sources(pasos)[0]["score"] == 0.0


def test_los_totales_son_de_lo_que_se_devuelve():
    pasos = [
        _paso(0, agent="investigador", tokens_in=100, tokens_out=50, latency_ms=1200.5),
        _paso(1, agent="redactor", tokens_in=300, tokens_out=900, latency_ms=8000.0),
        _paso(2, agent="revisor", tokens_in=200, tokens_out=40, latency_ms=900.0,
              iteration=1, status="error"),
    ]
    totales = ex.totals_of(pasos)
    assert totales["steps"] == 3
    assert totales["agents"] == ["investigador", "redactor", "revisor"]
    assert (totales["tokens_in"], totales["tokens_out"]) == (600, 990)
    assert totales["latency_ms"] == 10100.5
    # Vueltas del bucle revisor→redactor, no número de pasos.
    assert totales["loops"] == 1
    assert totales["failed_steps"] == 1


# ── Contra la API ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    from app.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _usuario(email: str, role: UserRole = UserRole.REDACTOR) -> UserModel:
    async with AsyncSessionLocal() as session:
        user = UserModel(
            email=email, hashed_password=hash_password("Contrasena-1234"),
            full_name=email.split("@")[0], role=role, is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _proyecto(nombre: str, owner_id=None) -> ProjectModel:
    async with AsyncSessionLocal() as session:
        proyecto = ProjectModel(name=nombre, description="", owner_id=owner_id)
        session.add(proyecto)
        await session.commit()
        await session.refresh(proyecto)
        return proyecto


async def _articulo(author_id, project_id=None, title="Un artículo") -> ArticleModel:
    async with AsyncSessionLocal() as session:
        articulo = ArticleModel(
            title=title, body="cuerpo", author_id=author_id, project_id=project_id
        )
        session.add(articulo)
        await session.commit()
        await session.refresh(articulo)
        return articulo


async def _pasos(article_id, filas):
    """Escribe la traza. `filas` son dicts; el instante lo pone el orden."""
    inicio = datetime(2026, 9, 4, 10, 0, 0)
    async with AsyncSessionLocal() as session:
        for posicion, fila in enumerate(filas):
            session.add(AgentRunStepModel(
                article_id=article_id,
                created_at=inicio + timedelta(seconds=posicion),
                **fila,
            ))
        await session.commit()


async def _token(ac: AsyncClient, email: str) -> str:
    resp = await ac.post(
        "/api/v1/auth/login", json={"email": email, "password": "Contrasena-1234"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_la_traza_llega_entera_con_fuentes_score_y_decision(db, client):
    """AC2 al pie de la letra: fuentes, score y decisiones por paso."""
    autor = await _usuario("autor@ejemplo.com")
    proyecto = await _proyecto("Proyecto", owner_id=autor.id)
    articulo = await _articulo(autor.id, proyecto.id)
    await _pasos(articulo.id, [
        dict(agent_name="investigador", step_index=0, model="qwen2.5:3b",
             params={"temperature": 0.2}, input_digest="Título: X",
             output_text="investigación", tokens_in=100, tokens_out=200,
             latency_ms=1500.0, rag_sources=[
                 {"doc_id": "d1", "title": "Corales", "score": 0.91, "chunk_ids": [1, 2]},
             ]),
        dict(agent_name="revisor", step_index=1, model="qwen2.5:3b",
             output_text="{}", tokens_in=300, tokens_out=40, latency_ms=900.0,
             decision={"score": 82.0, "coherent": True, "hitl_outcome": None},
             rationale="- Falta metodología"),
    ])

    async with client as ac:
        token = await _token(ac, autor.email)
        resp = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200, resp.text
    datos = resp.json()
    assert datos["available"] is True
    assert datos["executions"] == 1
    assert [p["agent_name"] for p in datos["steps"]] == ["investigador", "revisor"]

    # Las tres cosas que AC2 nombra.
    assert datos["sources"][0]["doc_id"] == "d1"
    assert datos["sources"][0]["title"] == "Corales"
    assert datos["steps"][1]["decision"]["score"] == 82.0
    assert "metodología" in datos["steps"][1]["rationale"]

    # Y lo que costó, que es la otra mitad de la explicación.
    assert datos["totals"]["tokens_out"] == 240
    assert datos["totals"]["agents"] == ["investigador", "revisor"]


@pytest.mark.asyncio
async def test_por_defecto_se_explica_la_ejecucion_que_produjo_el_texto(db, client):
    """Un artículo reejecutado: lo que se está leyendo lo produjo la última."""
    autor = await _usuario("reejecuta@ejemplo.com")
    articulo = await _articulo(autor.id)
    await _pasos(articulo.id, [
        dict(agent_name="investigador", step_index=0, output_text="primera"),
        dict(agent_name="redactor", step_index=1, output_text="primera"),
        dict(agent_name="investigador", step_index=0, output_text="segunda"),
        dict(agent_name="redactor", step_index=1, output_text="segunda"),
        dict(agent_name="revisor", step_index=2, output_text="segunda"),
    ])

    async with client as ac:
        token = await _token(ac, autor.email)
        cabeceras = {"Authorization": f"Bearer {token}"}
        ultima = await ac.get(f"/api/v1/agents/{articulo.id}/explain", headers=cabeceras)
        todas = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain?scope=all", headers=cabeceras
        )

    assert ultima.status_code == 200, ultima.text
    assert ultima.json()["scope"] == "last"
    assert len(ultima.json()["steps"]) == 3
    assert {p["output_text"] for p in ultima.json()["steps"]} == {"segunda"}
    # Pero se dice cuántas hay: el panel avisa de que hay historia detrás.
    assert ultima.json()["executions"] == 2

    assert len(todas.json()["steps"]) == 5
    assert todas.json()["scope"] == "all"


@pytest.mark.asyncio
async def test_un_scope_inventado_se_rechaza(db, client):
    autor = await _usuario("scope@ejemplo.com")
    articulo = await _articulo(autor.id)
    async with client as ac:
        token = await _token(ac, autor.email)
        resp = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain?scope=todo",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_un_articulo_sin_traza_lo_dice_en_vez_de_parecer_vacio(db, client):
    """Distinguir «no se ha ejecutado» de «la traza se purgó» es el motivo de
    `available`: la interfaz enseña estados distintos y solo uno tiene arreglo."""
    autor = await _usuario("sintraza@ejemplo.com")
    articulo = await _articulo(autor.id)
    async with client as ac:
        token = await _token(ac, autor.email)
        resp = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["available"] is False
    assert resp.json()["steps"] == []
    assert resp.json()["executions"] == 0


@pytest.mark.asyncio
async def test_la_traza_de_otra_persona_no_se_lee(db, client):
    """Mismo control de acceso que `/runs`: la unidad de acceso es el artículo."""
    autor = await _usuario("propietario@ejemplo.com")
    intruso = await _usuario("intruso@ejemplo.com")
    articulo = await _articulo(autor.id)
    await _pasos(articulo.id, [dict(agent_name="redactor", step_index=0)])

    async with client as ac:
        token = await _token(ac, intruso.email)
        resp = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_sin_autenticar_no_se_lee(db, client):
    autor = await _usuario("anon@ejemplo.com")
    articulo = await _articulo(autor.id)
    async with client as ac:
        resp = await ac.get(f"/api/v1/agents/{articulo.id}/explain")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_con_otro_proyecto_activo_el_articulo_no_aparece(db, client):
    """Defensa en profundidad de T8.5: la cabecera es opcional aquí —los
    endpoints de artículo no la piden—, pero si viene se comprueba. 404 y no
    403: la respuesta no debe distinguir «es de otro proyecto» de «no existe»."""
    autor = await _usuario("dosproyectos@ejemplo.com", role=UserRole.ADMIN)
    suyo = await _proyecto("Suyo", owner_id=autor.id)
    otro = await _proyecto("Otro", owner_id=autor.id)
    articulo = await _articulo(autor.id, suyo.id)
    await _pasos(articulo.id, [dict(agent_name="redactor", step_index=0)])

    async with client as ac:
        token = await _token(ac, autor.email)
        correcto = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain",
            headers={"Authorization": f"Bearer {token}", "X-Project-Id": str(suyo.id)},
        )
        cruzado = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain",
            headers={"Authorization": f"Bearer {token}", "X-Project-Id": str(otro.id)},
        )

    assert correcto.status_code == 200, correcto.text
    assert cruzado.status_code == 404


@pytest.mark.asyncio
async def test_un_articulo_inexistente_es_404(db, client):
    import uuid

    autor = await _usuario("nada@ejemplo.com")
    async with client as ac:
        token = await _token(ac, autor.email)
        resp = await ac.get(
            f"/api/v1/agents/{uuid.uuid4()}/explain",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


# ── Contra el pipeline real: que la suposición sea cierta ───────────────────

@pytest.fixture
def sin_registro_de_runs(monkeypatch):
    """`agent_runs` no es lo que se prueba aquí."""
    import uuid as _uuid

    from app.modules.agents.application import use_cases as orquestador

    async def _start(agent_name, article_id, author_id, input_payload):
        return _uuid.uuid4()

    async def _end(run_id, output_payload, status, error_message=None):
        return None

    monkeypatch.setattr(orquestador, "log_run_start", _start)
    monkeypatch.setattr(orquestador, "log_run_end", _end)


@pytest.mark.asyncio
async def test_reejecutar_de_verdad_produce_dos_ejecuciones(
    db, client, sin_registro_de_runs, monkeypatch
):
    """La separación se apoya en que el orquestador reinicia `step_index` en cada
    ejecución. Eso es una **suposición sobre otro módulo**, y leerla no basta:
    aquí se ejecuta el pipeline dos veces de verdad y se mira qué devuelve el
    endpoint. Si algún día el orquestador numera de otra forma, este test cae y
    no el panel en producción, que es donde no se vería."""
    from app.modules.agents.adapters import investigador as adapter_investigador
    from app.modules.agents.adapters import redactor as adapter_redactor
    from app.modules.agents.application import use_cases as orquestador

    async def investigador(state):
        ex.record_tokens(10, 5)
        return {"research_data": "material"}

    async def redactor(state):
        ex.record_tokens(20, 30)
        return {"draft_text": "# Borrador"}

    monkeypatch.setattr(adapter_investigador, "run_investigador", investigador)
    monkeypatch.setattr(adapter_redactor, "run_redactor", redactor)

    autor = await _usuario("pipeline@ejemplo.com")
    articulo = await _articulo(autor.id)

    for _ in range(2):
        await orquestador.Orchestrator.run(
            article_id=articulo.id, author_id=autor.id, title="Un título",
            keywords=["uno"], scientific_format="apa",
            flow_sequence=["investigador", "redactor"],
        )

    async with client as ac:
        token = await _token(ac, autor.email)
        resp = await ac.get(
            f"/api/v1/agents/{articulo.id}/explain",
            headers={"Authorization": f"Bearer {token}"},
        )

    datos = resp.json()
    assert datos["executions"] == 2, datos
    # Y por defecto se explica la última: dos agentes, no cuatro.
    assert [p["agent_name"] for p in datos["steps"]] == ["investigador", "redactor"]
    assert datos["totals"]["tokens_out"] == 35
