"""VAL-004 — `POST /agents/{id}/run` rechaza un orden inválido aunque se salte la UI."""
import pytest

from test_project_isolation import (  # noqa: F401  (fixtures y ayudas de ese módulo)
    _cabeceras, _proyecto, _token, _usuario, client, db,
)
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, UserRole


async def _articulo(email: str, cuerpo: str):
    autora = await _usuario(email, UserRole.REDACTOR)
    proyecto = await _proyecto("P", owner_id=autora.id)
    async with AsyncSessionLocal() as session:
        art = ArticleModel(title="T", body=cuerpo, author_id=autora.id,
                           project_id=proyecto.id, status=ArticleStatus.DRAFT)
        session.add(art)
        await session.commit()
        await session.refresh(art)
    return autora, proyecto, art.id


async def _run(client, autora, proyecto, articulo_id, secuencia, monkeypatch):
    import app.routers.agents as agents_router

    lanzados = []

    async def _fake(**kwargs):
        lanzados.append(kwargs)

    monkeypatch.setattr(agents_router.Orchestrator, "run", staticmethod(_fake))
    async with client as ac:
        token = await _token(ac, autora.email)
        resp = await ac.post(
            f"/api/v1/agents/{articulo_id}/run",
            json={"flow_sequence": secuencia, "agent_settings": {}},
            headers=_cabeceras(token, proyecto.id),
        )
    return resp, lanzados


@pytest.mark.asyncio
async def test_orden_invalido_se_rechaza_y_no_se_lanza_nada(db, client, monkeypatch):
    autora, proyecto, art = await _articulo("a1@ejemplo.com", "")
    resp, lanzados = await _run(client, autora, proyecto, art, ["publicador", "redactor"], monkeypatch)
    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"]["issues"][0]["code"] == "wrong_order"
    assert lanzados == []


@pytest.mark.asyncio
async def test_orden_valido_se_ejecuta(db, client, monkeypatch):
    autora, proyecto, art = await _articulo("a2@ejemplo.com", "")
    resp, lanzados = await _run(client, autora, proyecto, art, ["redactor", "revisor", "publicador"], monkeypatch)
    assert resp.status_code == 200, resp.text
    assert len(lanzados) == 1


@pytest.mark.asyncio
async def test_republicar_un_articulo_con_cuerpo_sigue_funcionando(db, client, monkeypatch):
    autora, proyecto, art = await _articulo("a3@ejemplo.com", "Texto ya redactado")
    resp, _ = await _run(client, autora, proyecto, art, ["formateador", "publicador"], monkeypatch)
    assert resp.status_code == 200, resp.text
