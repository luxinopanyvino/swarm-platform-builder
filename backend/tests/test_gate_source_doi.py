"""Aportar a mano el DOI de una referencia y reevaluar (#469)."""
import pytest

from test_gate_report_api import (  # noqa: F401  (fixtures y ayudas de ese módulo)
    _articulo, _cabeceras, _token, _usuario, client, db,
)
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, PublicationGateReportModel, UserRole
from app.platform.publication_gate import gate as gate_module
from app.platform.publication_gate.types import CriterionResult, CriterionStatus
from sqlalchemy import select

FUENTES = [
    {"title": "Sin DOI", "authors": "Ana Gil", "year": "2020", "journal": "J"},
    {"title": "Síntesis", "url": "synthesis://llm"},
    {"title": "Otra", "authors": "Luis Mir", "year": "2021", "journal": "K", "doi": "10.1/otra"},
]


async def _con_informe(email="autora@ejemplo.com"):
    autora, proyecto, art = await _articulo(email)
    async with AsyncSessionLocal() as s:
        s.add(PublicationGateReportModel(article_id=art.id, text_sha256="x", criteria={}, sources=FUENTES))
        await s.commit()
    return autora, proyecto, art


async def _poner(usuario, proyecto, art_id, index, doi):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, usuario.email)
        return await ac.put(
            f"/api/v1/articles/{art_id}/gate-report/sources/{index}",
            json={"doi": doi}, headers=_cabeceras(token, proyecto.id),
        )


@pytest.fixture
def vistas(monkeypatch):
    vistas = []

    async def falso(sources, cfg, **kw):
        vistas.append([dict(s) for s in sources])
        return CriterionResult("reference_existence", CriterionStatus.PASSED, []), list(sources)

    monkeypatch.setattr(gate_module, "check_reference_existence", falso)
    return vistas


@pytest.mark.asyncio
async def test_el_doi_se_pone_en_la_referencia_del_indice_y_se_reevalua(db, client, vistas):
    autora, proyecto, art = await _con_informe()
    # El índice cuenta solo las referencias citables: la 2.ª es «Otra», no la síntesis.
    r = await _poner(autora, proyecto, art.id, 2, "https://doi.org/10.1000/ABC")
    assert r.status_code == 200, r.text
    assert vistas[0][2]["doi"] == "10.1000/abc" and vistas[0][0].get("doi") is None
    assert r.json()["current"] is True
    async with AsyncSessionLocal() as s:
        ultimo = (await s.execute(
            select(PublicationGateReportModel).order_by(PublicationGateReportModel.created_at.desc())
        )).scalars().first()
    assert ultimo.sources[2]["doi"] == "10.1000/abc"


@pytest.mark.asyncio
async def test_se_rechaza_un_doi_mal_formado_o_un_indice_inexistente(db, client, vistas):
    autora, proyecto, art = await _con_informe()
    assert (await _poner(autora, proyecto, art.id, 1, "no-es-un-doi")).status_code == 422
    assert (await _poner(autora, proyecto, art.id, 3, "10.1/x")).status_code == 404
    assert (await _poner(autora, proyecto, art.id, 0, "10.1/x")).status_code == 404
    assert vistas == []


@pytest.mark.asyncio
async def test_solo_autor_revisor_o_admin_y_no_sobre_publicados(db, client, vistas):
    autora, proyecto, art = await _con_informe()
    ajena = await _usuario("ajena@ejemplo.com", UserRole.REDACTOR)
    assert (await _poner(ajena, proyecto, art.id, 1, "10.1/x")).status_code == 403

    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
        a.status = ArticleStatus.PUBLISHED
        await s.commit()
    assert (await _poner(autora, proyecto, art.id, 1, "10.1/x")).status_code == 409
    assert vistas == []
