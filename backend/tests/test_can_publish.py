"""SPEC-032 AC10 y AC13 / T20.11 — una sola puerta a `published` (PR-REG-04)."""
import itertools
import re
from pathlib import Path

import pytest
from sqlalchemy import select

from test_project_isolation import (  # noqa: F401  (fixtures y ayudas de ese módulo)
    _cabeceras, _proyecto, _token, _usuario, client, db,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, PublicationGateReportModel, UserRole
from app.platform.publication_gate import gate as gate_module
from app.platform.publication_gate.decision import (
    Approval, GateState, assign_published, can_publish, dev_seed_decision, legacy_decision,
)
from app.platform.publication_gate.service import text_sha256
from app.platform.publication_gate.types import CriterionResult, CriterionStatus

APP = Path(__file__).resolve().parents[1] / "app"
OK = {"review_status": "ok", "approval_score": 90, "coherent": True}


# ── AC10: la tabla de verdad ────────────────────────────────────────────────


def test_publica_solo_con_las_tres_cosas():
    d = can_publish(review=OK, gate=GateState(True, True), approval=Approval("u"))
    assert d.allowed and d.reasons == ()


REVISIONES = {
    "aprueba": OK,
    "80_justo": {"review_status": "ok", "approval_score": 80, "coherent": True},
    "79": {"review_status": "ok", "approval_score": 79, "coherent": True},
    "80_con_bloqueante": {"review_status": "ok", "approval_score": 80, "coherent": False},
    "no_verificada": {"review_status": "not_verified", "approval_score": 0, "coherent": False},
    "no_hubo": {"review_status": "not_run"},
    "ninguna": None,
}
COMPUERTAS = {
    "limpia": GateState(True, True), "con_bloqueantes": GateState(False, True),
    "caducada": GateState(True, False), "ninguna": None,
}
APROBACIONES = {"si": Approval("u"), "texto_cambiado": Approval("u", current=False), "no": None}


@pytest.mark.parametrize(
    "r,g,a", list(itertools.product(REVISIONES, COMPUERTAS, APROBACIONES)),
)
def test_tabla_de_verdad_completa(r, g, a):
    d = can_publish(review=REVISIONES[r], gate=COMPUERTAS[g], approval=APROBACIONES[a])
    esperado = r in ("aprueba", "80_justo") and g == "limpia" and a == "si"
    assert d.allowed is esperado, (r, g, a, d.reasons)
    assert d.allowed == (d.reasons == ())


def test_un_80_con_un_bloqueante_abierto_no_publica():
    d = can_publish(review=REVISIONES["80_con_bloqueante"], gate=GateState(True, True), approval=Approval("u"))
    assert not d.allowed and "not_coherent" in d.reasons


def test_modo_aviso_relaja_revision_y_compuerta_pero_no_la_aprobacion():
    mal = dict(review=REVISIONES["79"], gate=GateState(False, True))
    d = can_publish(**mal, approval=Approval("u"), enforce=False)
    assert d.allowed and {"score_below_threshold", "gate_blockers"} <= set(d.warnings)
    assert not can_publish(**mal, approval=None, enforce=False).allowed


def test_assign_published_exige_una_decision_que_lo_permita():
    class A:
        status = None
        published_at = None

    a = A()
    with pytest.raises(PermissionError):
        assign_published(a, can_publish(review=None, gate=None, approval=None))
    assert a.status is None
    assign_published(a, legacy_decision())
    assert a.status == ArticleStatus.PUBLISHED and a.published_at is not None


def test_la_siembra_de_desarrollo_solo_funciona_con_el_flag(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DEV_SEED", False)
    with pytest.raises(PermissionError):
        dev_seed_decision()
    monkeypatch.setattr(settings, "ENABLE_DEV_SEED", True)
    assert dev_seed_decision().allowed


# ── AC10: único punto de asignación, por inspección estática ────────────────

ASIGNACION = re.compile(r"(?<![=!<>])\bstatus\s*=\s*ArticleStatus\.PUBLISHED\b")
DECISION = APP / "platform" / "publication_gate" / "decision.py"
# Dominio hexagonal sin usar, con su propio enum (ver el test siguiente).
DOMINIO_HUERFANO = APP / "modules" / "articles"


def test_nada_asigna_published_salvo_can_publish():
    culpables = []
    for ruta in APP.rglob("*.py"):
        if ruta == DECISION or DOMINIO_HUERFANO in ruta.parents:
            continue
        for n, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if ASIGNACION.search(linea.split("#")[0]):
                culpables.append(f"{ruta.relative_to(APP)}:{n}: {linea.strip()}")
    assert culpables == [], "otra asignación de PUBLISHED fuera de decision.py:\n" + "\n".join(culpables)
    assert len(ASIGNACION.findall(DECISION.read_text(encoding="utf-8"))) == 1


def test_el_dominio_hexagonal_de_articulos_no_vuelve():
    """`modules/articles` tenía su propio `ArticleStatus` y un `publish()` que no pasaba por
    la compuerta; estaba muerto y se borró (DEC-5). Si reaparece, o alguien lo importa, este
    test falla: cualquier camino a `published` tiene que pasar por `can_publish`."""
    assert not DOMINIO_HUERFANO.exists(), "modules/articles reapareció: debe pasar por can_publish"
    for ruta in APP.rglob("*.py"):
        assert "app.modules.articles" not in ruta.read_text(encoding="utf-8"), ruta


# ── AC13: los tres caminos ──────────────────────────────────────────────────

CUERPO = "## Introducción\nTexto."


@pytest.fixture(autouse=True)
def _referencias_resueltas(monkeypatch):
    async def ok(sources, cfg, **kw):
        return CriterionResult("reference_existence", CriterionStatus.PASSED, []), list(sources)

    monkeypatch.setattr(gate_module, "check_reference_existence", ok)


async def _escenario(*, estado=ArticleStatus.IN_REVIEW, informe=True, review=OK):
    autora = await _usuario("autora@ejemplo.com", UserRole.REDACTOR)
    admin = await _usuario("admin@ejemplo.com", UserRole.ADMIN)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as s:
        art = ArticleModel(title="T", body=CUERPO, author_id=autora.id, project_id=proyecto.id,
                           status=estado, reviewer_id=admin.id, responsible_author_id=autora.id)
        s.add(art)
        await s.commit()
        await s.refresh(art)
        if informe:
            criteria = {"passed": True, "criteria": [], "pending": []}
            if review is not None:
                criteria["review"] = review
            s.add(PublicationGateReportModel(
                article_id=art.id, text_sha256=text_sha256(CUERPO), criteria=criteria,
                sources=[{"title": "Deep learning", "doi": "10.1/x"}]))
            await s.commit()
    return autora, admin, proyecto, art


async def _post(usuario, proyecto, ruta):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, usuario.email)
        return await ac.post(ruta, headers=_cabeceras(token, proyecto.id))


async def _estado(art_id):
    async with AsyncSessionLocal() as s:
        return (await s.execute(select(ArticleModel).where(ArticleModel.id == art_id))).scalars().first()


@pytest.mark.asyncio
@pytest.mark.parametrize("camino", ["approve", "publish"])
async def test_los_dos_endpoints_publican_con_las_tres_condiciones(db, client, camino):
    _, admin, proyecto, art = await _escenario()
    r = await _post(admin, proyecto, f"/api/v1/articles/{art.id}/{camino}")
    assert r.status_code == 200, r.text
    a = await _estado(art.id)
    assert a.status == ArticleStatus.PUBLISHED and a.approved_by == admin.id
    assert a.approved_text_sha256 == text_sha256(CUERPO)


@pytest.mark.asyncio
@pytest.mark.parametrize("camino", ["approve", "publish"])
@pytest.mark.parametrize("review,codigo", [
    (REVISIONES["79"], "score_below_threshold"),
    (REVISIONES["no_verificada"], "review_not_verified"),
    (None, "review_missing"),
])
async def test_sin_revision_que_apruebe_ninguno_publica(db, client, camino, review, codigo):
    _, admin, proyecto, art = await _escenario(review=review)
    r = await _post(admin, proyecto, f"/api/v1/articles/{art.id}/{camino}")
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == codigo
    assert (await _estado(art.id)).status != ArticleStatus.PUBLISHED


@pytest.mark.asyncio
async def test_publish_sobre_un_borrador_sin_compuerta_la_evalua_y_no_publica(db, client):
    # AC13: antes publicaba cualquier borrador. Sin informe, evalúa; el texto no es IMRaD → bloquea.
    _, admin, proyecto, art = await _escenario(estado=ArticleStatus.DRAFT, informe=False)
    r = await _post(admin, proyecto, f"/api/v1/articles/{art.id}/publish")
    assert r.status_code == 409, r.text
    assert (await _estado(art.id)).status == ArticleStatus.DRAFT
    async with AsyncSessionLocal() as s:
        informes = (await s.execute(select(PublicationGateReportModel))).scalars().all()
    assert len(informes) == 1  # se evaluó y quedó registrado


@pytest.mark.asyncio
async def test_publish_reevalua_si_el_informe_es_de_otro_texto(db, client):
    _, admin, proyecto, art = await _escenario()
    async with AsyncSessionLocal() as s:
        a = await _estado(art.id)
        a.body = "## Introducción\nTexto cambiado."
        s.add(a)
        await s.commit()
    r = await _post(admin, proyecto, f"/api/v1/articles/{art.id}/publish")
    # El informe viejo se descarta y se evalúa el texto actual (que no es IMRaD completo).
    assert r.status_code == 409
    async with AsyncSessionLocal() as s:
        n = len((await s.execute(select(PublicationGateReportModel))).scalars().all())
    assert n == 2


@pytest.mark.asyncio
async def test_publish_ya_no_lo_hace_un_redactor_ni_el_propietario(db, client):
    autora, _, proyecto, art = await _escenario()
    r = await _post(autora, proyecto, f"/api/v1/articles/{art.id}/publish")
    assert r.status_code == 403
    assert (await _estado(art.id)).status == ArticleStatus.IN_REVIEW


@pytest.mark.asyncio
async def test_la_siembra_ya_no_deja_el_ejemplo_por_fuera_de_la_puerta(db):
    fuente = (APP / "main.py").read_text(encoding="utf-8")
    assert "assign_published(ejemplo_publicado, dev_seed_decision())" in fuente
