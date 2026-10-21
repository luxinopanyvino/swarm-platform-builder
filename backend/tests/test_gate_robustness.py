"""Un fallo de la compuerta no se traga (DEC-6) y la aprobación bloquea la fila (DEC-7)."""
import inspect

import pytest

from test_publicador_compuerta import (  # noqa: F401  (fixtures y ayudas de ese módulo)
    IMRAD, _articulo, _leer, _publicar, _referencias_resueltas, db,
)
from app.models import ArticleStatus
from app.platform.publication_gate import service
from app.routers import articles


@pytest.mark.asyncio
async def test_si_falla_la_escritura_del_informe_el_publicador_lo_deja_subir(db, monkeypatch):
    _, art = await _articulo()

    async def roto(*a, **kw):
        raise RuntimeError("la base de datos no responde")

    monkeypatch.setattr(service, "evaluate_and_store", roto)
    logs = []
    with pytest.raises(RuntimeError, match="no responde"):
        await _publicar(art, IMRAD, logs=logs)
    # La persona lo ve en el registro del paso y el artículo no cambia de estado.
    assert any(nivel == "error" and "no pudo completar" in m for nivel, m in logs)
    a, informes = await _leer(art.id)
    assert a.status == ArticleStatus.DRAFT and informes == []


def test_approve_y_publish_toman_el_bloqueo_de_la_fila():
    """SQLite ignora `FOR UPDATE`; en Postgres es lo que serializa las aprobaciones."""
    for endpoint in (articles.approve_article, articles.publish_article_direct):
        assert ".with_for_update()" in inspect.getsource(endpoint), endpoint.__name__


def test_tras_reevaluar_se_vuelve_a_bloquear_y_a_comprobar_el_estado():
    fuente = inspect.getsource(articles._publish_through_the_gate)
    despues = fuente.split("evaluate_and_store(", 1)[1]
    assert "with_for_update=True" in despues
    assert despues.index("with_for_update=True") < despues.index("approval_denial(")
