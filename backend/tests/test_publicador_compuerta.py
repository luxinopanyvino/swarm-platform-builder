"""SPEC-032 AC5, AC8 y AC14 / T20.9 — la compuerta en el Publicador."""
import inspect
from pathlib import Path

import pytest
from sqlalchemy import select

from test_project_isolation import _proyecto, _usuario, db  # noqa: F401  (fixtures y ayudas)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, PublicationGateReportModel, UserRole
from app.modules.agents.adapters import publicador
from app.modules.agents.domain import alejandria
from app.platform.publication_gate import gate as gate_module
from app.platform.publication_gate.types import CriterionResult, CriterionStatus

IMRAD = """## Introducción
Texto.

## Metodología
Texto.

## Resultados
Texto.

## Discusión
Texto.

## Referencias
Lista.
"""

FUENTE = {"title": "Deep learning", "authors": "LeCun, Bengio, Hinton", "year": "2015",
          "journal": "Nature", "doi": "10.1038/nature14539"}


@pytest.fixture(autouse=True)
def _referencias_resueltas(monkeypatch):
    """Sin red: todas las referencias existen y coinciden."""

    async def ok(sources, cfg, **kw):
        return CriterionResult("reference_existence", CriterionStatus.PASSED, []), list(sources)

    monkeypatch.setattr(gate_module, "check_reference_existence", ok)


async def _articulo(estado=ArticleStatus.DRAFT, **extra):
    autora = await _usuario("autora@ejemplo.com", UserRole.REDACTOR)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as s:
        art = ArticleModel(title="T", body="", author_id=autora.id, project_id=proyecto.id,
                           status=estado, **extra)
        s.add(art)
        await s.commit()
        await s.refresh(art)
    return autora, art


async def _publicar(art, texto, fuentes=(FUENTE,), logs=None):
    state = {
        "article_id": art.id, "formatted_text": texto, "sources": list(fuentes),
        "_log": (lambda m, lvl="info": logs.append((lvl, m))) if logs is not None else None,
    }
    state = {k: v for k, v in state.items() if v is not None}
    return await publicador.run_publicador(state)


async def _leer(art_id):
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art_id))).scalars().first()
        informes = (await s.execute(select(PublicationGateReportModel).where(
            PublicationGateReportModel.article_id == art_id))).scalars().all()
    return a, informes


@pytest.mark.asyncio
async def test_sin_bloqueantes_queda_en_revision_y_nunca_publicado(db):
    _, art = await _articulo()
    res = await _publicar(art, IMRAD)
    a, informes = await _leer(art.id)
    assert a.status == ArticleStatus.IN_REVIEW  # AC8: jamás `published` desde el agente
    assert a.published_at is None and res["published_url"] == ""
    assert res["gate_failed"] is False and res["gate_blockers"] == []
    assert a.body == IMRAD
    assert len(informes) == 1  # AC6: se guarda el informe


@pytest.mark.asyncio
async def test_el_informe_se_evalua_sobre_el_texto_final_y_lo_liga_por_huella(db):
    from app.platform.publication_gate.service import is_current

    _, art = await _articulo()
    await _publicar(art, IMRAD)
    a, informes = await _leer(art.id)
    assert is_current(informes[0], a)
    assert informes[0].criteria["passed"] is True
    assert {p["id"] for p in informes[0].criteria["pending"]} >= {"V01", "V12"}  # AC5


@pytest.mark.asyncio
async def test_con_bloqueantes_vuelve_a_borrador_con_agente_responsable(db):
    _, art = await _articulo(estado=ArticleStatus.IN_REVIEW)
    res = await _publicar(art, IMRAD + "\nTODO revisar")
    a, informes = await _leer(art.id)
    assert a.status == ArticleStatus.DRAFT  # AC14
    assert res["gate_failed"] is True
    bloqueo = res["gate_blockers"][0]
    assert bloqueo["criterion"] == "placeholders" and bloqueo["responsible_agent"] == "redactor"
    assert bloqueo["evidence"][0]["pattern"] == "TODO"
    assert informes[0].criteria["passed"] is False


@pytest.mark.asyncio
async def test_sin_estructura_el_bloqueante_apunta_al_redactor(db):
    _, art = await _articulo()
    res = await _publicar(art, "Un párrafo sin secciones.")
    assert [b["criterion"] for b in res["gate_blockers"]] == ["imrad_structure"]
    assert res["gate_blockers"][0]["responsible_agent"] == "redactor"


@pytest.mark.asyncio
async def test_sin_fuentes_estructuradas_no_se_aprueba_por_ausencia(db):
    _, art = await _articulo()
    res = await _publicar(art, IMRAD, fuentes=())
    assert res["gate_failed"] is True
    assert res["gate_blockers"][0]["criterion"] == "reference_existence"
    assert res["gate_blockers"][0]["responsible_agent"] == "investigador"


@pytest.mark.asyncio
async def test_modo_aviso_registra_pero_llega_a_revision(db, monkeypatch):
    monkeypatch.setattr(settings, "PUBLICATION_GATE_ENFORCE", False)
    _, art = await _articulo()
    logs = []
    res = await _publicar(art, IMRAD + "\nTODO", logs=logs)
    a, informes = await _leer(art.id)
    assert a.status == ArticleStatus.IN_REVIEW and res["gate_failed"] is False
    assert informes[0].criteria["passed"] is False  # el bloqueante consta igualmente
    assert any(lvl == "warning" and "ENFORCE=false" in m for lvl, m in logs)


@pytest.mark.asyncio
async def test_reejecutar_un_articulo_publicado_exige_aprobar_de_nuevo(db):
    import datetime

    autora, art = await _articulo(estado=ArticleStatus.PUBLISHED)
    async with AsyncSessionLocal() as s:
        a = (await s.execute(select(ArticleModel).where(ArticleModel.id == art.id))).scalars().first()
        a.approved_by, a.approved_at = autora.id, datetime.datetime.utcnow()
        a.approved_text_sha256, a.published_at = "x" * 64, datetime.datetime.utcnow()
        await s.commit()
    await _publicar(art, IMRAD)
    a, _ = await _leer(art.id)
    assert a.status == ArticleStatus.IN_REVIEW
    assert a.approved_by is None and a.approved_at is None and a.approved_text_sha256 is None
    assert a.published_at is None


@pytest.mark.asyncio
async def test_un_proyecto_sin_compuerta_conserva_el_comportamiento_anterior(db, monkeypatch):
    from dataclasses import replace

    sin_gate = replace(alejandria.package(), gate=None)
    monkeypatch.setattr(alejandria, "package", lambda: sin_gate)
    _, art = await _articulo()
    res = await _publicar(art, "Texto sin más")
    a, informes = await _leer(art.id)
    assert a.status == ArticleStatus.PUBLISHED and informes == []
    assert res["published_url"].endswith("/view")


def test_use_cases_emite_gate_failed_con_los_bloqueantes():
    from app.modules.agents.application import use_cases

    fuente = inspect.getsource(use_cases)
    assert '"type": "gate_failed"' in fuente and 'res.get("gate_failed")' in fuente
    assert 'enriched_state["_run_id"] = run_id' in fuente


def test_el_publicador_sigue_sin_llamar_al_llm():
    fuente = Path(publicador.__file__).read_text(encoding="utf-8")
    assert "call_llm" not in fuente


def test_gate_responsible_debe_nombrar_un_agente_declarado(tmp_path):
    import shutil

    import yaml

    from app.platform.projects import loader

    raiz = tmp_path / "p"
    shutil.copytree(loader.PROJECTS_ROOT / "alejandria-magazine", raiz)
    ruta = raiz / loader.PLANTILLA
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    datos["gate"]["responsible"]["placeholders"] = "agente-fantasma"
    ruta.write_text(yaml.safe_dump(datos, allow_unicode=True), encoding="utf-8")
    with pytest.raises(loader.TemplateError, match="agente-fantasma"):
        loader.load_from(raiz)
