"""SPEC-032 AC6 / T20.6 — informe de la compuerta persistido y API de lectura/reevaluación."""
import pytest
from sqlalchemy import func, select

from test_project_isolation import (  # noqa: F401  (fixtures y ayudas de ese módulo)
    _cabeceras, _proyecto, _token, _usuario, client, db,
)
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, PublicationGateReportModel, UserRole
from app.platform.publication_gate import gate as gate_module
from app.platform.publication_gate.service import text_sha256
from app.platform.publication_gate.types import CriterionResult, CriterionStatus


async def _articulo(email="autora@ejemplo.com", cuerpo="## Introducción\nTexto."):
    autora = await _usuario(email, UserRole.REDACTOR)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as session:
        art = ArticleModel(title="T", body=cuerpo, author_id=autora.id,
                           project_id=proyecto.id, status=ArticleStatus.DRAFT)
        session.add(art)
        await session.commit()
        await session.refresh(art)
    return autora, proyecto, art


async def _llamar(client, usuario, proyecto, metodo, ruta):
    # Un cliente nuevo por llamada: el de la fixture no se puede reabrir.
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, usuario.email)
        return await getattr(ac, metodo)(ruta, headers=_cabeceras(token, proyecto.id))


async def _cuenta():
    async with AsyncSessionLocal() as s:
        return (await s.execute(select(func.count()).select_from(PublicationGateReportModel))).scalar()


@pytest.mark.asyncio
async def test_articulo_sin_informe_se_muestra_sin_informe(db, client):
    autora, proyecto, art = await _articulo()
    r = await _llamar(client, autora, proyecto, "get", f"/api/v1/articles/{art.id}/gate-report")
    assert r.status_code == 200, r.text
    assert r.json() == {"report": None, "current": False}


@pytest.mark.asyncio
async def test_reevaluar_guarda_un_informe_ligado_al_texto(db, client):
    autora, proyecto, art = await _articulo()
    r = await _llamar(client, autora, proyecto, "post", f"/api/v1/articles/{art.id}/gate-report")
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["current"] is True
    assert cuerpo["report"]["text_sha256"] == text_sha256(art.body)
    criterios = {c["criterion"]: c for c in cuerpo["report"]["criteria"]["criteria"]}
    # Sin fuentes estructuradas, las referencias no se aprueban por ausencia.
    assert criterios["reference_existence"]["status"] == "not_verified"
    assert criterios["imrad_structure"]["status"] == "failed"
    assert cuerpo["report"]["criteria"]["passed"] is False
    assert {p["id"] for p in cuerpo["report"]["criteria"]["pending"]} >= {"V01", "V12"}


@pytest.mark.asyncio
async def test_cada_evaluacion_crea_otra_fila_y_el_texto_cambiado_invalida(db, client):
    autora, proyecto, art = await _articulo()
    ruta = f"/api/v1/articles/{art.id}/gate-report"
    await _llamar(client, autora, proyecto, "post", ruta)
    await _llamar(client, autora, proyecto, "post", ruta)
    assert await _cuenta() == 2  # no sobrescribe

    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
        a.body = "Otro texto distinto"
        await s.commit()
    r = await _llamar(client, autora, proyecto, "get", ruta)
    assert r.json()["current"] is False  # el informe describe el texto anterior
    r = await _llamar(client, autora, proyecto, "post", ruta)
    assert r.json()["current"] is True and await _cuenta() == 3


@pytest.mark.asyncio
async def test_la_reevaluacion_reutiliza_las_fuentes_del_ultimo_informe(db, client, monkeypatch):
    autora, proyecto, art = await _articulo()
    async with AsyncSessionLocal() as s:
        s.add(PublicationGateReportModel(
            article_id=art.id, text_sha256="x", criteria={}, sources=[{"title": "Guardada", "doi": "10.1/x"}],
        ))
        await s.commit()
    vistas = []

    async def falso(sources, cfg, **kw):
        vistas.append(list(sources))
        return CriterionResult("reference_existence", CriterionStatus.PASSED, []), list(sources)

    monkeypatch.setattr(gate_module, "check_reference_existence", falso)
    r = await _llamar(client, autora, proyecto, "post", f"/api/v1/articles/{art.id}/gate-report")
    assert r.status_code == 200, r.text
    assert vistas == [[{"title": "Guardada", "doi": "10.1/x"}]]


@pytest.mark.asyncio
async def test_solo_autor_revisor_asignado_o_admin(db, client):
    autora, proyecto, art = await _articulo()
    ruta = f"/api/v1/articles/{art.id}/gate-report"
    ajena = await _usuario("ajena@ejemplo.com", UserRole.REDACTOR)
    assert (await _llamar(client, ajena, proyecto, "get", ruta)).status_code == 403
    assert (await _llamar(client, ajena, proyecto, "post", ruta)).status_code == 403

    admin = await _usuario("admin@ejemplo.com", UserRole.ADMIN)
    assert (await _llamar(client, admin, proyecto, "get", ruta)).status_code == 200

    revisora = await _usuario("revisora@ejemplo.com", UserRole.REDACTOR)
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
        a.reviewer_id = revisora.id
        await s.commit()
    assert (await _llamar(client, revisora, proyecto, "get", ruta)).status_code == 200


@pytest.mark.asyncio
async def test_sin_sesion_no_hay_informe(db, client):
    _, _, art = await _articulo()
    async with client as ac:
        r = await ac.get(f"/api/v1/articles/{art.id}/gate-report")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_articulo_inexistente(db, client):
    import uuid

    autora, proyecto, _ = await _articulo()
    r = await _llamar(client, autora, proyecto, "get", f"/api/v1/articles/{uuid.uuid4()}/gate-report")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_el_estado_requires_human_review_se_puede_guardar(db):
    autora, _, art = await _articulo()
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
        a.status = ArticleStatus.REQUIRES_HUMAN_REVIEW
        a.responsible_author_id = autora.id
        a.approved_by = autora.id
        a.approved_text_sha256 = text_sha256(a.body)
        await s.commit()
        await s.refresh(a)
        assert a.status.value == "requires_human_review"
        assert a.responsible_author_id == autora.id and a.approved_at is None


def test_la_huella_es_sha256_del_texto():
    assert text_sha256("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert text_sha256(None) == text_sha256("")
    assert text_sha256("a") != text_sha256("b")
