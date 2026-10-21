"""SPEC-032 AC8 / T20.10 — aprobación humana explícita (PR-REG-05, PR-REG-06)."""
import pytest
from sqlalchemy import select

from test_project_isolation import (  # noqa: F401  (fixtures y ayudas de ese módulo)
    _cabeceras, _proyecto, _token, _usuario, client, db,
)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import (
    ArticleModel, ArticleStatus, PublicationGateReportModel, UserRole,
)
from app.models.audit_log import AuditLogModel
from app.platform.publication_gate.service import text_sha256

CUERPO = "## Introducción\nTexto."


async def _escenario(*, informe="vigente", responsable=True, estado=ArticleStatus.IN_REVIEW):
    """Autora (propietaria), revisora asignada y un artículo `in_review`."""
    autora = await _usuario("autora@ejemplo.com", UserRole.REDACTOR)
    revisora = await _usuario("revisora@ejemplo.com", UserRole.REDACTOR)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as s:
        art = ArticleModel(
            title="T", body=CUERPO, author_id=autora.id, project_id=proyecto.id,
            status=estado, reviewer_id=revisora.id,
            responsible_author_id=autora.id if responsable else None,
        )
        s.add(art)
        await s.commit()
        await s.refresh(art)
        if informe:
            s.add(PublicationGateReportModel(
                article_id=art.id,
                text_sha256=text_sha256(CUERPO if informe != "viejo" else "otro texto"),
                criteria={"passed": informe != "bloqueado", "criteria": [], "pending": []},
                sources=[],
            ))
            await s.commit()
    return autora, revisora, proyecto, art


async def _aprobar(client, usuario, proyecto, art):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, usuario.email)
        return await ac.post(f"/api/v1/articles/{art.id}/approve", headers=_cabeceras(token, proyecto.id))


async def _articulo(art_id):
    async with AsyncSessionLocal() as s:
        return (await s.execute(select(ArticleModel).where(ArticleModel.id == art_id))).scalars().first()


@pytest.mark.asyncio
async def test_el_revisor_asignado_aprueba_y_queda_registrado(db, client):
    autora, revisora, proyecto, art = await _escenario()
    r = await _aprobar(client, revisora, proyecto, art)
    assert r.status_code == 200, r.text
    a = await _articulo(art.id)
    assert a.status == ArticleStatus.PUBLISHED
    assert a.approved_by == revisora.id and a.approved_at is not None
    assert a.approved_text_sha256 == text_sha256(CUERPO)
    async with AsyncSessionLocal() as s:
        fila = (await s.execute(select(AuditLogModel).where(AuditLogModel.action == "article.approved"))).scalars().first()
    assert fila is not None and fila.detail["decision"] == "approved"
    assert fila.detail["text_sha256"] == text_sha256(CUERPO)


@pytest.mark.asyncio
async def test_un_admin_que_no_es_propietario_tambien_puede(db, client):
    _, _, proyecto, art = await _escenario()
    admin = await _usuario("admin@ejemplo.com", UserRole.ADMIN)
    assert (await _aprobar(client, admin, proyecto, art)).status_code == 200


@pytest.mark.asyncio
async def test_el_propietario_no_se_aprueba_a_si_mismo(db, client):
    autora, _, proyecto, art = await _escenario()
    async with AsyncSessionLocal() as s:
        a = await _articulo(art.id)
        a.reviewer_id = autora.id  # incluso siendo además el revisor asignado
        s.add(a)
        await s.commit()
    r = await _aprobar(client, autora, proyecto, art)
    assert r.status_code == 403
    assert (await _articulo(art.id)).status == ArticleStatus.IN_REVIEW


@pytest.mark.asyncio
async def test_un_admin_propietario_tampoco(db, client):
    admin = await _usuario("admin@ejemplo.com", UserRole.ADMIN)
    proyecto = await _proyecto("P", owner_id=admin.id)
    async with AsyncSessionLocal() as s:
        art = ArticleModel(title="T", body=CUERPO, author_id=admin.id, project_id=proyecto.id,
                           status=ArticleStatus.IN_REVIEW, responsible_author_id=admin.id)
        s.add(art)
        await s.commit()
        await s.refresh(art)
        s.add(PublicationGateReportModel(article_id=art.id, text_sha256=text_sha256(CUERPO),
                                         criteria={"passed": True}, sources=[]))
        await s.commit()
    assert (await _aprobar(client, admin, proyecto, art)).status_code == 403


@pytest.mark.asyncio
async def test_la_autoaprobacion_de_desarrollo_la_permite(db, client, monkeypatch):
    autora, _, proyecto, art = await _escenario()
    async with AsyncSessionLocal() as s:
        a = await _articulo(art.id)
        a.reviewer_id = autora.id
        s.add(a)
        await s.commit()
    monkeypatch.setattr(settings, "PUBLICATION_ALLOW_SELF_APPROVAL", True)
    assert (await _aprobar(client, autora, proyecto, art)).status_code == 200


def test_la_autoaprobacion_no_se_puede_encender_en_produccion():
    from app.core.config import _DEV_ONLY_FLAGS, _disable_dev_only_flags

    assert "PUBLICATION_ALLOW_SELF_APPROVAL" in _DEV_ONLY_FLAGS
    cfg = {"DEBUG": False, "PUBLICATION_ALLOW_SELF_APPROVAL": True}
    _disable_dev_only_flags(cfg)
    assert cfg["PUBLICATION_ALLOW_SELF_APPROVAL"] is False


@pytest.mark.asyncio
async def test_una_persona_ajena_recibe_403(db, client):
    _, _, proyecto, art = await _escenario()
    ajena = await _usuario("ajena@ejemplo.com", UserRole.REDACTOR)
    assert (await _aprobar(client, ajena, proyecto, art)).status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kwargs,codigo",
    [
        ({"informe": None}, "no_gate_report"),
        ({"informe": "viejo"}, "text_changed"),
        ({"informe": "bloqueado"}, "gate_blockers"),
        ({"responsable": False}, "no_responsible_author"),
    ],
)
async def test_409_si_la_compuerta_no_lo_permite(db, client, kwargs, codigo):
    _, revisora, proyecto, art = await _escenario(**kwargs)
    r = await _aprobar(client, revisora, proyecto, art)
    assert r.status_code == 409, r.text
    assert r.json()["detail"]["code"] == codigo
    a = await _articulo(art.id)
    assert a.status == ArticleStatus.IN_REVIEW and a.approved_by is None


@pytest.mark.asyncio
async def test_modo_aviso_no_bloquea_pero_lo_deja_en_el_registro(db, client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLICATION_GATE_ENFORCE", False)
    _, revisora, proyecto, art = await _escenario(informe="bloqueado")
    assert (await _aprobar(client, revisora, proyecto, art)).status_code == 200
    async with AsyncSessionLocal() as s:
        fila = (await s.execute(select(AuditLogModel).where(AuditLogModel.action == "article.approved"))).scalars().first()
    assert fila.detail["gate_warning"] == "gate_blockers"


@pytest.mark.asyncio
async def test_modo_aviso_sigue_exigiendo_aprobacion_humana(db, client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLICATION_GATE_ENFORCE", False)
    _, _, proyecto, art = await _escenario(informe=None)
    ajena = await _usuario("ajena@ejemplo.com", UserRole.REDACTOR)
    assert (await _aprobar(client, ajena, proyecto, art)).status_code == 403


@pytest.mark.asyncio
async def test_solo_se_aprueba_lo_que_esta_en_revision(db, client):
    _, revisora, proyecto, art = await _escenario(estado=ArticleStatus.DRAFT)
    assert (await _aprobar(client, revisora, proyecto, art)).status_code == 409


# ── Autor responsable ───────────────────────────────────────────────────────


async def _declarar(client, usuario, proyecto, art, destino):
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        token = await _token(ac, usuario.email)
        return await ac.put(
            f"/api/v1/articles/{art.id}/responsible-author",
            json={"user_id": str(destino)}, headers=_cabeceras(token, proyecto.id),
        )


@pytest.mark.asyncio
async def test_la_autora_declara_al_responsable(db, client):
    autora, _, proyecto, art = await _escenario(responsable=False)
    r = await _declarar(client, autora, proyecto, art, autora.id)
    assert r.status_code == 200 and r.json()["responsible_author_id"] == str(autora.id)


@pytest.mark.asyncio
async def test_solo_la_autora_o_un_admin_declaran(db, client):
    _, revisora, proyecto, art = await _escenario(responsable=False)
    assert (await _declarar(client, revisora, proyecto, art, revisora.id)).status_code == 403


@pytest.mark.asyncio
async def test_el_responsable_debe_ser_un_usuario_activo(db, client):
    import uuid

    autora, _, proyecto, art = await _escenario(responsable=False)
    assert (await _declarar(client, autora, proyecto, art, uuid.uuid4())).status_code == 422
