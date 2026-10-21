"""SPEC-032 AC7 / T20.8 — tras agotar las vueltas sin aprobar, revisión humana."""
import uuid

import pytest
from sqlalchemy import select

from test_project_isolation import _proyecto, _usuario, db  # noqa: F401  (fixtures y ayudas)
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, UserRole
from app.modules.agents.adapters import (
    formateador as adapter_formateador,
    investigador as adapter_investigador,
    publicador as adapter_publicador,
    redactor as adapter_redactor,
    revisor as adapter_revisor,
)
from app.modules.agents.application import use_cases as orquestador
from app.platform.engine.routing import FIN, ReviewLoop, make_review_router, review_exhausted

BUCLE = ReviewLoop(reviewer="revisor", on_reject="redactor", threshold=80, max_loops=3, on_exhausted="stop")
FLUJO = ["investigador", "redactor", "revisor", "formateador", "publicador"]


def _estado(**kw):
    return {"flow_sequence": FLUJO, **kw}


# ── Enrutador ───────────────────────────────────────────────────────────────


def test_con_vueltas_disponibles_sigue_volviendo_al_redactor():
    ruta = make_review_router(BUCLE)
    assert ruta(_estado(approval_score=50, loop_count=2)) == "redactor"


def test_agotadas_las_vueltas_con_stop_termina_sin_formatear_ni_publicar():
    ruta = make_review_router(BUCLE)
    assert ruta(_estado(approval_score=50, loop_count=3)) == FIN


def test_con_advance_el_comportamiento_anterior_se_conserva():
    avanza = ReviewLoop(reviewer="revisor", on_reject="redactor", max_loops=3)
    assert make_review_router(avanza)(_estado(approval_score=50, loop_count=3)) == "formateador"


def test_una_revision_que_aprueba_avanza_aunque_haya_dado_vueltas():
    ruta = make_review_router(BUCLE)
    assert ruta(_estado(approval_score=85, coherent=True, loop_count=3)) == "formateador"


def test_la_incoherencia_con_buena_puntuacion_tambien_cuenta():
    ruta = make_review_router(BUCLE)
    assert ruta(_estado(approval_score=90, coherent=False, loop_count=1)) == "redactor"
    assert ruta(_estado(approval_score=90, coherent=False, loop_count=3)) == FIN


def test_una_decision_humana_de_continuar_manda_sobre_el_agotamiento():
    ruta = make_review_router(BUCLE)
    estado = _estado(approval_score=50, loop_count=3, user_decision="continue")
    assert ruta(estado) == "formateador"
    assert review_exhausted(BUCLE, estado) is False


def test_revision_no_verificada_agota_las_vueltas_como_cualquier_otra():
    ruta = make_review_router(BUCLE)
    assert ruta(_estado(approval_score=0, coherent=False, review_status="not_verified", loop_count=3)) == FIN


def test_el_revisor_cuenta_la_vuelta_tambien_por_incoherencia():
    import asyncio

    async def llm(*a, **k):
        return '{"approval_score": 92, "coherent": false, "feedback": ["incoherente"]}'

    original = adapter_revisor.call_llm
    adapter_revisor.call_llm = llm
    try:
        out = asyncio.run(adapter_revisor.run_revisor(
            {"draft_text": "x", "loop_count": 1, "agent_settings": {}}))
    finally:
        adapter_revisor.call_llm = original
    assert out["loop_count"] == 2 and out["coherent"] is False


def test_la_plantilla_de_alejandria_se_detiene_al_agotar():
    from app.modules.agents.domain import alejandria

    assert alejandria.review_loop().on_exhausted == "stop"


def test_on_exhausted_invalido_falla_al_cargar(tmp_path):
    import shutil

    import yaml

    from app.platform.projects import loader

    raiz = tmp_path / "p"
    shutil.copytree(loader.PROJECTS_ROOT / "alejandria-magazine", raiz)
    ruta = raiz / loader.PLANTILLA
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    datos["graph"]["review_loops"][0]["on_exhausted"] = "explotar"
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(loader.TemplateError, match="on_exhausted"):
        loader.load_from(raiz)


# ── El pipeline completo ────────────────────────────────────────────────────


@pytest.fixture
def pipeline(monkeypatch):
    llamados, eventos = [], []

    async def _log_start(agent_name, article_id, author_id, input_payload):
        return uuid.uuid4()

    async def _log_end(run_id, output_payload, status, error_message=None):
        return None

    async def _log_step(**kw):
        return None

    monkeypatch.setattr(orquestador, "log_run_start", _log_start)
    monkeypatch.setattr(orquestador, "log_run_end", _log_end)
    monkeypatch.setattr(orquestador, "log_run_step", _log_step)
    monkeypatch.setattr(orquestador, "publish_event", lambda aid, ev: eventos.append(ev))

    def agente(nombre, salida):
        async def runner(state):
            llamados.append(nombre)
            return dict(salida(state))
        return runner

    monkeypatch.setattr(adapter_investigador, "run_investigador",
                        agente("investigador", lambda s: {"research_data": "d", "sources": []}))
    monkeypatch.setattr(adapter_redactor, "run_redactor",
                        agente("redactor", lambda s: {"draft_text": f"borrador {len(llamados)}"}))
    monkeypatch.setattr(adapter_revisor, "run_revisor", agente("revisor", lambda s: {
        "approval_score": 55, "coherent": False, "review_status": "ok",
        "feedback": ["Falta rigor", "Sin discusión"],
        "loop_count": (s.get("loop_count") or 0) + 1, "user_decision": None}))
    monkeypatch.setattr(adapter_formateador, "run_formateador",
                        agente("formateador", lambda s: {"formatted_text": "x"}))
    monkeypatch.setattr(adapter_publicador, "run_publicador",
                        agente("publicador", lambda s: {"published_url": ""}))
    return llamados, eventos


async def _articulo():
    autora = await _usuario("autora@ejemplo.com", UserRole.REDACTOR)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as s:
        art = ArticleModel(title="T", body="", author_id=autora.id, project_id=proyecto.id,
                           status=ArticleStatus.DRAFT)
        s.add(art)
        await s.commit()
        await s.refresh(art)
    return autora, art


@pytest.mark.asyncio
async def test_tres_vueltas_sin_aprobar_detienen_el_pipeline_para_una_persona(db, pipeline):
    llamados, eventos = pipeline
    autora, art = await _articulo()
    await orquestador.Orchestrator.run(
        article_id=art.id, author_id=autora.id, title="T", keywords=[],
        scientific_format="apa", flow_sequence=FLUJO,
    )
    # El revisor corrió 3 veces y ni el Formateador ni el Publicador llegaron a correr.
    assert llamados.count("revisor") == 3 and llamados.count("redactor") == 3
    assert "formateador" not in llamados and "publicador" not in llamados

    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
    assert a.status == ArticleStatus.REQUIRES_HUMAN_REVIEW
    assert a.body.startswith("borrador")  # la persona ve el último borrador
    assert "Falta rigor" in a.rejection_comment  # y los comentarios del revisor

    evento = next(e for e in eventos if e["type"] == "requires_human_review")
    assert evento["score"] == 55 and evento["loops"] == 3
    assert evento["feedback"] == ["Falta rigor", "Sin discusión"]
    assert [e["type"] for e in eventos].index("requires_human_review") < [e["type"] for e in eventos].index("done")


@pytest.mark.asyncio
async def test_una_revision_que_aprueba_no_detiene_el_pipeline(db, pipeline, monkeypatch):
    llamados, eventos = pipeline

    async def aprueba(state):
        llamados.append("revisor")
        return {"approval_score": 90, "coherent": True, "review_status": "ok", "feedback": [],
                "loop_count": 0, "user_decision": None}

    monkeypatch.setattr(adapter_revisor, "run_revisor", aprueba)
    autora, art = await _articulo()
    await orquestador.Orchestrator.run(
        article_id=art.id, author_id=autora.id, title="T", keywords=[],
        scientific_format="apa", flow_sequence=FLUJO,
    )
    assert "publicador" in llamados
    assert not any(e["type"] == "requires_human_review" for e in eventos)
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
    assert a.status == ArticleStatus.DRAFT  # el Publicador simulado no cambió el estado


# ── Salir del estado: solo una persona ──────────────────────────────────────


async def _con_estado(estado):
    autora = await _usuario("a@ejemplo.com", UserRole.REDACTOR)
    revisora = await _usuario("r@ejemplo.com", UserRole.REDACTOR)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as s:
        art = ArticleModel(title="T", body="b", author_id=autora.id, project_id=proyecto.id,
                           status=estado, reviewer_id=revisora.id, rejection_comment="Falta rigor")
        s.add(art)
        await s.commit()
        await s.refresh(art)
    return autora, revisora, proyecto, art


@pytest.mark.asyncio
async def test_rechazar_desde_requires_human_review_pasa_a_rejected(db):
    from httpx import ASGITransport, AsyncClient

    from app.main import app
    from test_project_isolation import _cabeceras, _token

    _, revisora, proyecto, art = await _con_estado(ArticleStatus.REQUIRES_HUMAN_REVIEW)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, revisora.email)
        r = await ac.post(f"/api/v1/articles/{art.id}/reject", params={"comment": "No procede"},
                          headers=_cabeceras(token, proyecto.id))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_reejecutar_devuelve_a_draft_y_conserva_los_comentarios(db, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    import app.routers.agents as agents_router
    from app.main import app
    from test_project_isolation import _cabeceras, _token

    lanzados = []

    async def _fake(**kwargs):
        lanzados.append(kwargs)

    monkeypatch.setattr(agents_router.Orchestrator, "run", staticmethod(_fake))
    autora, _, proyecto, art = await _con_estado(ArticleStatus.REQUIRES_HUMAN_REVIEW)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, autora.email)
        r = await ac.post(f"/api/v1/agents/{art.id}/run",
                          json={"flow_sequence": ["redactor", "revisor", "publicador"], "agent_settings": {}},
                          headers=_cabeceras(token, proyecto.id))
    assert r.status_code == 200, r.text
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
    assert a.status == ArticleStatus.DRAFT and a.rejection_comment == "Falta rigor"


@pytest.mark.asyncio
async def test_reanudar_no_saca_el_estado_ni_reinicia_el_contador(db, monkeypatch):
    from httpx import ASGITransport, AsyncClient

    import app.routers.agents as agents_router
    from app.main import app
    from test_project_isolation import _cabeceras, _token

    async def _fake(**kwargs):
        return None

    monkeypatch.setattr(agents_router.Orchestrator, "run", staticmethod(_fake))
    autora, _, proyecto, art = await _con_estado(ArticleStatus.REQUIRES_HUMAN_REVIEW)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, autora.email)
        await ac.post(f"/api/v1/agents/{art.id}/run?resume=true",
                      json={"flow_sequence": ["redactor", "revisor"], "agent_settings": {}},
                      headers=_cabeceras(token, proyecto.id))
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
    assert a.status == ArticleStatus.REQUIRES_HUMAN_REVIEW


def test_la_reanudacion_continua_del_checkpoint_y_no_reinicia_el_contador():
    import inspect

    fuente = inspect.getsource(orquestador.Orchestrator.run)
    assert "graph_input = None if local_resume else initial_state" in fuente
