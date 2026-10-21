"""SPEC-032 AC16 / T20.13 — retención de informes, egress y despliegue gradual."""
import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from test_project_isolation import _proyecto, _usuario, db  # noqa: F401  (fixtures y ayudas)
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models import ArticleModel, ArticleStatus, PublicationGateReportModel, UserRole
from app.platform import egress, metrics, retention
from app.platform.publication_gate.gate import evaluate_gate
from app.platform.publication_gate.reference_resolver import (
    CROSSREF, OPENALEX, ResolverConfig, check_reference_existence,
)

# ── Retención ───────────────────────────────────────────────────────────────


async def _informe(session, articulo, dias):
    session.add(PublicationGateReportModel(
        article_id=articulo.id, text_sha256="x" * 64, criteria={}, sources=[],
        created_at=datetime.utcnow() - timedelta(days=dias),
    ))


async def _articulo(session, autor, estado):
    art = ArticleModel(title="T", body="b", author_id=autor.id, status=estado)
    session.add(art)
    await session.flush()
    return art


async def _cuenta():
    async with AsyncSessionLocal() as s:
        return (await s.execute(select(func.count()).select_from(PublicationGateReportModel))).scalar()


@pytest.mark.asyncio
async def test_los_informes_viejos_de_articulos_no_publicados_caducan(db):
    autor = await _usuario("a@ejemplo.com", UserRole.REDACTOR)
    async with AsyncSessionLocal() as s:
        borrador = await _articulo(s, autor, ArticleStatus.DRAFT)
        await _informe(s, borrador, 120)   # caduca
        await _informe(s, borrador, 10)    # reciente: se queda
        await s.commit()
    async with AsyncSessionLocal() as s:
        simulado = await retention.purge(s, apply=False)
    assert simulado.counts["gate_reports"] == 1 and await _cuenta() == 2  # simular no borra
    async with AsyncSessionLocal() as s:
        await retention.purge(s, apply=True)
    assert await _cuenta() == 1


@pytest.mark.asyncio
async def test_el_informe_de_un_articulo_publicado_no_caduca(db):
    autor = await _usuario("a@ejemplo.com", UserRole.REDACTOR)
    async with AsyncSessionLocal() as s:
        publicado = await _articulo(s, autor, ArticleStatus.PUBLISHED)
        await _informe(s, publicado, 400)  # es la evidencia de la aprobación
        revision = await _articulo(s, autor, ArticleStatus.IN_REVIEW)
        await _informe(s, revision, 400)   # este sí caduca
        await s.commit()
    async with AsyncSessionLocal() as s:
        await retention.purge(s, apply=True)
    async with AsyncSessionLocal() as s:
        restantes = (await s.execute(select(PublicationGateReportModel))).scalars().all()
    assert len(restantes) == 1
    assert restantes[0].article_id == publicado.id


@pytest.mark.asyncio
async def test_una_ventana_a_cero_conserva_los_informes(db, monkeypatch):
    monkeypatch.setattr(settings, "RETENTION_GATE_REPORTS_DAYS", 0)
    autor = await _usuario("a@ejemplo.com", UserRole.REDACTOR)
    async with AsyncSessionLocal() as s:
        await _informe(s, await _articulo(s, autor, ArticleStatus.DRAFT), 999)
        await s.commit()
    async with AsyncSessionLocal() as s:
        resultado = await retention.purge(s, apply=True)
    assert "gate_reports" in resultado.skipped and await _cuenta() == 1


def test_el_ajuste_de_retencion_tiene_valor_y_entrada_en_la_configuracion_yaml():
    from pathlib import Path

    assert settings.RETENTION_GATE_REPORTS_DAYS == 90
    for ruta in (Path(__file__).resolve().parents[1] / "config.yaml",
                 Path(__file__).resolve().parents[2] / "config.yaml"):
        assert "gate_reports_days: 90" in ruta.read_text(encoding="utf-8")


# ── Egress ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sin_dns(monkeypatch):
    monkeypatch.setattr(egress, "_resolver", lambda host, port: ["93.184.216.34"])


def test_con_allowlist_la_compuerta_alcanza_crossref_y_openalex(sin_dns, monkeypatch):
    monkeypatch.setattr(settings, "EGRESS_ALLOWED_DOMAINS", "ejemplo.org")
    for host in egress.HOSTS_COMPUERTA:
        assert egress.is_egress_allowed(f"https://{host}/works", quien=egress.QUIEN_COMPUERTA).allowed


def test_pero_el_modelo_no_gana_esos_hosts(sin_dns, monkeypatch):
    monkeypatch.setattr(settings, "EGRESS_ALLOWED_DOMAINS", "ejemplo.org")
    for host in egress.HOSTS_COMPUERTA:
        assert not egress.is_egress_allowed(f"https://{host}/works").allowed
        assert not egress.is_egress_allowed(f"https://{host}/works", quien="fetch_url").allowed


def test_sin_allowlist_no_cambia_nada_y_lo_interno_sigue_bloqueado(sin_dns, monkeypatch):
    monkeypatch.setattr(settings, "EGRESS_ALLOWED_DOMAINS", "")
    assert egress.is_egress_allowed("https://api.crossref.org/works", quien=egress.QUIEN_COMPUERTA).allowed
    monkeypatch.setattr(egress, "_resolver", lambda host, port: ["127.0.0.1"])
    assert not egress.is_egress_allowed("https://api.crossref.org/works", quien=egress.QUIEN_COMPUERTA).allowed


def test_el_resolutor_llama_a_la_puerta_con_el_nombre_de_la_compuerta():
    import inspect

    from app.platform.publication_gate import reference_resolver

    assert 'quien="publication_gate"' in inspect.getsource(reference_resolver._default_fetch)
    assert egress.QUIEN_COMPUERTA == "publication_gate"


# ── Privacidad: solo metadatos de referencias ───────────────────────────────

SECRETO = "MANUSCRITO-INEDITO-NO-DEBE-SALIR"


class _Resp:
    status_code = 200

    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def test_el_texto_del_manuscrito_nunca_sale_hacia_crossref_ni_openalex():
    vistas = []

    async def fetch(url, *, params=None, headers=None, timeout=10.0):
        vistas.append(repr((url, params, headers)))
        if url.startswith(CROSSREF + "/"):
            return _Resp({"message": {
                "DOI": "10.1/x", "title": ["Deep learning"], "type": "journal-article",
                "author": [{"family": "LeCun"}], "issued": {"date-parts": [[2015]]},
                "container-title": ["Nature"]}})
        return _Resp({"message": {"items": []}, "results": []})

    from app.modules.agents.domain import alejandria

    async def nosleep(_):
        pass

    fuentes = [
        {"title": "Deep learning", "authors": "LeCun", "year": "2015", "journal": "Nature", "doi": "10.1/x"},
        {"title": "Sin DOI", "authors": "Alguien", "year": "", "journal": "", "doi": ""},
    ]
    texto = f"## Introducción\n{SECRETO}\n"
    asyncio.run(evaluate_gate(texto, fuentes, alejandria.package().gate, fetch=fetch, sleep=nosleep))
    assert vistas, "el test no ejercitó ninguna consulta"
    assert not any(SECRETO in v for v in vistas)


# ── Contacto, métricas y despliegue gradual ─────────────────────────────────


def test_el_user_agent_lleva_el_correo_de_configuracion(monkeypatch):
    monkeypatch.setattr(settings, "PUBLICATION_GATE_CONTACT_EMAIL", "contacto@ejemplo.org")
    cabeceras = []

    async def fetch(url, *, params=None, headers=None, timeout=10.0):
        cabeceras.append(headers)
        return _Resp({"message": {
            "DOI": "10.1/x", "title": ["T"], "type": "journal-article",
            "author": [{"family": "A"}], "issued": {"date-parts": [[2020]]}, "container-title": ["N"]}})

    async def nosleep(_):
        pass

    asyncio.run(check_reference_existence(
        [{"title": "T", "authors": "A", "year": "2020", "journal": "N", "doi": "10.1/x"}],
        ResolverConfig(), fetch=fetch, sleep=nosleep))
    assert "mailto:contacto@ejemplo.org" in cabeceras[0]["User-Agent"]


def test_se_registran_metricas_por_criterio_y_por_resultado_de_referencia():
    antes = metrics.render_metrics()[0].decode()

    async def fetch(url, *, params=None, headers=None, timeout=10.0):
        raise TimeoutError("x")

    async def nosleep(_):
        pass

    from app.modules.agents.domain import alejandria

    asyncio.run(evaluate_gate("## Introducción\nx", [{"title": "T", "authors": "A", "doi": "10.1/z"}],
                              alejandria.package().gate, fetch=fetch, sleep=nosleep))
    despues = metrics.render_metrics()[0].decode()
    assert 'publication_gate_criterion_total{criterion="reference_existence",status="not_verified"}' in despues
    assert 'publication_gate_reference_total{outcome="not_verified"}' in despues
    assert 'publication_gate_external_errors_total{provider="crossref",reason="network"}' in despues
    assert despues != antes


def test_el_modo_aviso_y_el_correo_se_leen_de_la_configuracion_yaml():
    from app.core import config

    assert "PUBLICATION_GATE_ENFORCE" in config.Settings.model_fields
    # Sin configuración, bloquea (falla cerrada); el despliegue gradual (DEC-4) lo
    # declara el yaml, que gana al valor por defecto del código.
    assert config.Settings.model_fields["PUBLICATION_GATE_ENFORCE"].default is True
    import yaml
    from pathlib import Path

    raiz = Path(__file__).resolve().parents[2]
    valores = {yaml.safe_load((raiz / r).read_text(encoding="utf-8"))["publication"]["gate_enforce"]
               for r in ("config.yaml", "backend/config.yaml")}
    assert len(valores) == 1 and isinstance(valores.pop(), bool),         "config.yaml y backend/config.yaml deben coincidir y declarar un booleano"
    # Los tests fijan la variable de entorno (conftest): el entorno gana al yaml.
    assert settings.PUBLICATION_GATE_ENFORCE is True
    assert settings.PUBLICATION_GATE_CONTACT_EMAIL == "" or "@" in settings.PUBLICATION_GATE_CONTACT_EMAIL
