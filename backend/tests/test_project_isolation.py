"""Aislamiento entre proyectos (SPEC-013 / T8.5 / AC6).

AC6: dos proyectos con documentos RAG distintos, cuando uno ejecuta su pipeline,
solo recuperan **lo suyo**; ni documentos del otro proyecto ni del seed de demo.

Antes de esta tarea no había ninguna noción de proyecto en la capa RAG, y la fuga
tenía tres puertas distintas —las tres se prueban aquí:

1. **La colección salía del perfil del agente.** Dos proyectos creados desde la
   misma plantilla nacen con el mismo `investigador` y el mismo
   `rag_collection: rag_docs`, así que sus documentos caían en la misma colección
   y en el mismo bucket.
2. **`rag_collection` lo escribe la persona usuaria** en el editor de agentes:
   aunque cada proyecto tuviera su colección, bastaba teclear la del vecino.
3. **La consulta de perfiles de la ejecución no filtraba por proyecto.** `slug` no
   es único entre proyectos, así que el pipeline podía arrancar con el modelo, el
   prompt y los `rag_doc_ids` de otro proyecto según el orden de la base.
"""
import os
import sys
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

TEST_DB_PATH = (ROOT_DIR / "tests" / "test_project_isolation.db").resolve()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH.as_posix()}"

from sqlalchemy import select  # noqa: E402

from app.core.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models import (  # noqa: E402
    AgentProfileModel, ProjectModel, UserModel, UserRole,
)
from app.platform.project_context import (  # noqa: E402
    ProjectContext, bucket_of, collection_for_state, is_project_collection,
    resolve_collection, sanitize_bucket,
)


# ── El nombre de la colección se deriva, no se recibe ────────────────────────

def test_dos_proyectos_con_el_mismo_bucket_no_comparten_coleccion():
    """El caso exacto de la fuga: misma plantilla, mismo perfil, mismo bucket."""
    uno = ProjectContext(UUID(int=1))
    otro = ProjectContext(UUID(int=2))
    assert uno.collection("rag_docs") != otro.collection("rag_docs")
    assert not uno.owns_collection(otro.collection("rag_docs"))


def test_la_biblioteca_compartida_lo_es_dentro_del_proyecto():
    """`__library__` es un bucket, así que hereda el aislamiento de la colección."""
    uno = ProjectContext(UUID(int=1))
    otro = ProjectContext(UUID(int=2))
    assert uno.collection("__library__") != otro.collection("__library__")


@pytest.mark.parametrize(
    "escrito_por_el_usuario",
    [
        "p_00000000000000000000000000000002__rag_docs",  # la colección del vecino
        "../../otro_proyecto",
        "rag_docs/../../etc",
        "RAG DOCS con espacios",
        "",
        None,
    ],
)
def test_el_perfil_no_puede_salirse_de_su_proyecto(escrito_por_el_usuario):
    """`rag_collection` es un campo de texto del editor de agentes.

    Pase lo que pase por ahí, el resultado tiene que seguir dentro del proyecto:
    de eso depende que el aislamiento no sea solo una convención.
    """
    mio = ProjectContext(UUID(int=1))
    ajeno = ProjectContext(UUID(int=2))
    resuelto = mio.collection(escrito_por_el_usuario)
    assert mio.owns_collection(resuelto)
    assert not ajeno.owns_collection(resuelto)
    assert "/" not in resuelto and ".." not in resuelto


def test_el_bucket_se_puede_volver_a_leer_para_la_interfaz():
    """La persona usuaria ve su nombre, no el identificador interno."""
    contexto = ProjectContext(UUID(int=1))
    assert bucket_of(contexto.collection("mis_fuentes")) == "mis_fuentes"
    assert is_project_collection(contexto.collection("x"))
    assert not is_project_collection("rag_docs")


def test_sin_proyecto_no_se_inventa_uno():
    assert resolve_collection(None, "rag_docs") == "rag_docs"
    assert sanitize_bucket(None) == "rag_docs"


def test_el_estado_del_grafo_resuelve_la_coleccion_del_proyecto():
    estado = {"project_id": UUID(int=9)}
    assert collection_for_state(estado, "rag_docs") == ProjectContext(UUID(int=9)).collection("rag_docs")


def test_una_ejecucion_sin_proyecto_avisa_en_los_logs(caplog):
    """El camino heredado sigue existiendo, pero no en silencio."""
    import logging

    with caplog.at_level(logging.WARNING):
        assert collection_for_state({}, "rag_docs") == "rag_docs"
    assert any("project_id" in r.message for r in caplog.records)


# ── De extremo a extremo: dos proyectos, dos conjuntos de documentos ─────────

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


async def _usuario(email: str, role: UserRole = UserRole.ADMIN) -> UserModel:
    async with AsyncSessionLocal() as session:
        user = UserModel(
            email=email,
            hashed_password=hash_password("Contrasena-1234"),
            full_name=email.split("@")[0],
            role=role,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


async def _proyecto(nombre: str, owner_id=None, is_system: bool = False) -> ProjectModel:
    async with AsyncSessionLocal() as session:
        proyecto = ProjectModel(
            name=nombre, description="", owner_id=owner_id, is_system=is_system
        )
        session.add(proyecto)
        await session.commit()
        await session.refresh(proyecto)
        return proyecto


async def _perfil(project_id, slug: str, **campos) -> AgentProfileModel:
    async with AsyncSessionLocal() as session:
        perfil = AgentProfileModel(
            project_id=project_id, slug=slug, name=slug.title(), **campos
        )
        session.add(perfil)
        await session.commit()
        await session.refresh(perfil)
        return perfil


async def _token(ac: AsyncClient, email: str) -> str:
    resp = await ac.post(
        "/api/v1/auth/login", json={"email": email, "password": "Contrasena-1234"}
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _cabeceras(token: str, project_id) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Project-Id": str(project_id)}


@pytest.mark.asyncio
async def test_los_documentos_de_un_proyecto_no_aparecen_en_el_otro(db, client, monkeypatch):
    """El escenario de AC6, contra la API real."""
    import app.routers.agents as agents_router

    indexado: dict[str, list[str]] = {}

    async def _fake_list_documents(qdrant_url, collection, agent_name, api_key=None):
        return [{"doc_id": d, "filename": f"{d}.md", "chunks": 1}
                for d in indexado.get(collection, [])]

    monkeypatch.setattr(agents_router, "list_documents", _fake_list_documents)
    monkeypatch.setattr(
        agents_router, "get_rag_backend", lambda *a, **k: _async_valor("local")
    )

    duenna = await _usuario("duenna@ejemplo.com")
    uno = await _proyecto("Proyecto uno", owner_id=duenna.id)
    otro = await _proyecto("Proyecto dos", owner_id=duenna.id)

    # Cada proyecto indexa lo suyo, en el bucket que el perfil llama igual.
    indexado[ProjectContext(uno.id).collection("rag_docs")] = ["doc-de-uno"]
    indexado[ProjectContext(otro.id).collection("rag_docs")] = ["doc-de-dos"]

    async with client as ac:
        token = await _token(ac, duenna.email)
        vista_uno = await ac.get(
            "/api/v1/agents/investigador/rag/documents", headers=_cabeceras(token, uno.id)
        )
        vista_otro = await ac.get(
            "/api/v1/agents/investigador/rag/documents", headers=_cabeceras(token, otro.id)
        )

    assert vista_uno.status_code == 200, vista_uno.text
    ids_uno = [d["doc_id"] for d in vista_uno.json()["documents"]]
    ids_otro = [d["doc_id"] for d in vista_otro.json()["documents"]]
    assert ids_uno == ["doc-de-uno"]
    assert ids_otro == ["doc-de-dos"]


async def _async_valor(valor):
    return valor


@pytest.mark.asyncio
async def test_sin_cabecera_de_proyecto_el_endpoint_no_adivina(db, client):
    """Antes respondía con los documentos de la colección común."""
    usuario = await _usuario("sincabecera@ejemplo.com")
    async with client as ac:
        token = await _token(ac, usuario.email)
        resp = await ac.get(
            "/api/v1/agents/investigador/rag/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "X-Project-Id" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_apuntar_al_proyecto_de_otra_persona_no_lo_abre(db, client):
    """Y responde 404, no 403: un 403 confirmaría que ese proyecto existe."""
    ajena = await _usuario("ajena@ejemplo.com", UserRole.REDACTOR)
    intrusa = await _usuario("intrusa@ejemplo.com", UserRole.REDACTOR)
    suyo = await _proyecto("Proyecto ajeno", owner_id=ajena.id)

    async with client as ac:
        token = await _token(ac, intrusa.email)
        resp = await ac.get(
            "/api/v1/agents/investigador/rag/documents", headers=_cabeceras(token, suyo.id)
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_un_proyecto_inexistente_tampoco(db, client):
    usuario = await _usuario("fantasma@ejemplo.com")
    async with client as ac:
        token = await _token(ac, usuario.email)
        resp = await ac.get(
            "/api/v1/agents/investigador/rag/documents", headers=_cabeceras(token, uuid4())
        )
    assert resp.status_code == 404


# ── La consulta de perfiles de la ejecución ─────────────────────────────────

@pytest.mark.asyncio
async def test_el_pipeline_usa_el_perfil_de_su_proyecto_y_no_el_homonimo(db, client, monkeypatch):
    """`slug` no es único entre proyectos: sin filtro, ganaba el que devolviera la base."""
    from app.models import ArticleModel, ArticleStatus

    lanzados: list[dict] = []

    async def _fake_run(**kwargs):
        lanzados.append(kwargs)

    import app.routers.agents as agents_router
    monkeypatch.setattr(agents_router.Orchestrator, "run", staticmethod(_fake_run))

    autora = await _usuario("autora@ejemplo.com", UserRole.REDACTOR)
    mio = await _proyecto("El mío", owner_id=autora.id)
    ajeno = await _proyecto("El ajeno", owner_id=autora.id)

    # Dos perfiles homónimos, con modelos distintos. El del proyecto ajeno se
    # crea primero para que sea el que una consulta sin filtro encontraría antes.
    await _perfil(ajeno.id, "investigador", model="modelo-ajeno")
    await _perfil(mio.id, "investigador", model="modelo-mio")

    async with AsyncSessionLocal() as session:
        articulo = ArticleModel(
            title="Un artículo",
            body="",
            author_id=autora.id,
            project_id=mio.id,
            status=ArticleStatus.DRAFT,
        )
        session.add(articulo)
        await session.commit()
        await session.refresh(articulo)
        articulo_id = articulo.id

    async with client as ac:
        token = await _token(ac, autora.email)
        resp = await ac.post(
            f"/api/v1/agents/{articulo_id}/run",
            json={"flow_sequence": ["investigador"], "agent_settings": {}},
            headers=_cabeceras(token, mio.id),
        )

    assert resp.status_code == 200, resp.text
    assert len(lanzados) == 1
    ajustes = lanzados[0]["agent_settings"]["investigador"]
    assert ajustes["model"] == "modelo-mio", "se coló el perfil del otro proyecto"
    assert lanzados[0]["project"].project_id == mio.id


@pytest.mark.asyncio
async def test_un_articulo_sin_proyecto_no_ejecuta_el_pipeline(db, client, monkeypatch):
    """Sin proyecto no hay dónde aislar: mejor negarse que caer al espacio común."""
    from app.models import ArticleModel, ArticleStatus

    import app.routers.agents as agents_router

    async def _fake_run(**kwargs):
        raise AssertionError("no debería haberse lanzado")

    monkeypatch.setattr(agents_router.Orchestrator, "run", staticmethod(_fake_run))

    autora = await _usuario("huerfana@ejemplo.com", UserRole.REDACTOR)
    async with AsyncSessionLocal() as session:
        articulo = ArticleModel(
            title="Sin proyecto", body="", author_id=autora.id,
            project_id=None, status=ArticleStatus.DRAFT,
        )
        session.add(articulo)
        await session.commit()
        await session.refresh(articulo)
        articulo_id = articulo.id

    async with client as ac:
        token = await _token(ac, autora.email)
        resp = await ac.post(
            f"/api/v1/agents/{articulo_id}/run",
            json={"flow_sequence": ["investigador"], "agent_settings": {}},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 409


# ── Perfiles de agente: editar y borrar los del vecino ──────────────────────

@pytest.mark.asyncio
async def test_no_se_puede_editar_el_perfil_de_otro_proyecto(db, client):
    autora = await _usuario("editora@ejemplo.com")
    mio = await _proyecto("Mío", owner_id=autora.id)
    ajeno = await _proyecto("Ajeno", owner_id=autora.id)
    perfil_ajeno = await _perfil(ajeno.id, "redactor", model="intacto")

    async with client as ac:
        token = await _token(ac, autora.email)
        resp = await ac.put(
            f"/api/v1/agents/claude-defs/{perfil_ajeno.id}",
            json={"content": '{"model": "reescrito"}'},
            headers=_cabeceras(token, mio.id),
        )
    assert resp.status_code == 404

    async with AsyncSessionLocal() as session:
        vigente = (await session.execute(
            select(AgentProfileModel).where(AgentProfileModel.id == perfil_ajeno.id)
        )).scalars().first()
        assert vigente.model == "intacto"


@pytest.mark.asyncio
async def test_no_se_puede_borrar_el_perfil_de_otro_proyecto(db, client):
    autora = await _usuario("borradora2@ejemplo.com")
    mio = await _proyecto("Mío", owner_id=autora.id)
    ajeno = await _proyecto("Ajeno", owner_id=autora.id)
    perfil_ajeno = await _perfil(ajeno.id, "personalizado", model="m")

    async with client as ac:
        token = await _token(ac, autora.email)
        resp = await ac.delete(
            f"/api/v1/agents/claude-defs/{perfil_ajeno.id}",
            headers=_cabeceras(token, mio.id),
        )
    assert resp.status_code == 404

    async with AsyncSessionLocal() as session:
        sigue = (await session.execute(
            select(AgentProfileModel).where(AgentProfileModel.id == perfil_ajeno.id)
        )).scalars().first()
        assert sigue is not None


# ── El aislamiento no se puede olvidar en el siguiente endpoint ──────────────

def test_todo_endpoint_que_toca_rag_declara_el_proyecto():
    """Guardia estructural: el motivo de que el proyecto sea una **dependencia**.

    Un parámetro más en la firma se olvida en la siguiente ruta que alguien
    añada, y el olvido no rompe nada visible: simplemente vuelve a leer la
    colección común. Esto lo convierte en un fallo de test.
    """
    import ast

    ruta = ROOT_DIR / "app" / "routers" / "agents.py"
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))

    #: Rutas que tocan documentos RAG y por tanto necesitan proyecto.
    def es_ruta_rag(decorador) -> bool:
        if not isinstance(decorador, ast.Call) or not decorador.args:
            return False
        primero = decorador.args[0]
        return isinstance(primero, ast.Constant) and "rag" in str(primero.value).lower()

    sin_proyecto = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, (ast.AsyncFunctionDef, ast.FunctionDef)):
            continue
        if not any(es_ruta_rag(d) for d in nodo.decorator_list):
            continue
        argumentos = [a.arg for a in nodo.args.args + nodo.args.kwonlyargs]
        if "project" not in argumentos:
            sin_proyecto.append(nodo.name)

    assert sin_proyecto == [], (
        "estos endpoints RAG no declaran `project` y volverían a leer la colección "
        f"común: {sin_proyecto}"
    )


def test_ningun_adapter_resuelve_la_coleccion_por_su_cuenta():
    """Los tres adapters pasan por `collection_for_state`, que es lo que aísla."""
    import re

    adapters = ROOT_DIR / "app" / "modules" / "agents" / "adapters"
    culpables = []
    for fichero in sorted(adapters.glob("*.py")):
        texto = fichero.read_text(encoding="utf-8")
        for numero, linea in enumerate(texto.splitlines(), 1):
            if re.search(r"^\s*rag_collection\s*=", linea) and "collection_for_state" not in linea:
                culpables.append(f"{fichero.name}:{numero}")
    assert culpables == [], (
        f"resuelven la colección sin pasar por el proyecto: {culpables}"
    )


# ── Migración de lo heredado ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_la_migracion_mueve_lo_heredado_al_proyecto_del_sistema(db, tmp_path, monkeypatch):
    """Lo ya subido debe seguir viéndose tras el cambio, o la migración no sirve."""
    import importlib.util
    import json

    from app.platform.capabilities import rag as rag_cap

    almacen = tmp_path / "rag_store"
    (almacen / "rag_docs").mkdir(parents=True)
    (almacen / "rag_docs" / "doc-viejo.json").write_text(
        json.dumps({"doc_id": "doc-viejo", "agent_name": "__library__",
                    "filename": "viejo.md", "chunks": [{"chunk_index": 0, "text": "hola"}]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(rag_cap, "_local_rag_root", lambda: almacen)

    sistema = await _proyecto("Sistema", is_system=True)

    spec = importlib.util.spec_from_file_location(
        "migrar", ROOT_DIR.parent / "scripts" / "migrate_rag_namespaces.py"
    )
    migrar = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migrar)
    monkeypatch.setattr(migrar, "_local_rag_root", lambda: almacen)

    destino = ProjectContext(sistema.id).collection("rag_docs")

    # Simulacro: no escribe nada.
    await migrar.migrar(aplicar=False, borrar_heredado=False)
    assert not (almacen / destino).exists()

    await migrar.migrar(aplicar=True, borrar_heredado=False)
    assert (almacen / destino / "doc-viejo.json").exists()
    assert (almacen / "rag_docs" / "doc-viejo.json").exists(), "no debe destruir el original"

    # Idempotente: repetirla no duplica ni falla.
    await migrar.migrar(aplicar=True, borrar_heredado=False)
    assert len(list((almacen / destino).glob("*.json"))) == 1
