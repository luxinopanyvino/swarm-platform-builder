"""SPEC-032 AC3 / medición real — lo que se aprendió al medir contra Crossref/OpenAlex.

La medición con la red (`scripts/measure_reference_resolution.py`) destapó dos
rigideces del resolutor que los registros simulados no ven; aquí quedan fijadas sin
red. También se comprueba el propio conjunto de medición y el resumen del script.
"""
import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

from app.platform.publication_gate import CriterionStatus
from app.platform.publication_gate.reference_resolver import (
    CROSSREF, OPENALEX, ResolverConfig, check_reference_existence, journals_match,
)

REPO = Path(__file__).resolve().parents[2]


# ── Revista: medido con «Proc. IEEE Conf. Computer Vision…» frente a Crossref ─


@pytest.mark.parametrize(
    "cita,registro",
    [
        ("Proc. IEEE Conf. Computer Vision and Pattern Recognition (CVPR)",
         "2016 IEEE Conference on Computer Vision and Pattern Recognition (CVPR)"),
        ("Proc. Natl. Acad. Sci.", "Proceedings of the National Academy of Sciences"),
        ("J. Mach. Learn. Res.", "Journal of Machine Learning Research"),
        ("Neural Comput.", "Neural Computation"),
        ("Machine Learning", "Machine Learning"),
    ],
)
def test_la_misma_publicacion_citada_de_otra_forma_coincide(cita, registro):
    assert journals_match(cita, registro)


@pytest.mark.parametrize(
    "cita,registro",
    [
        ("Science", "Nature"),
        ("Nature", "Science"),
        ("Neural Networks", "Machine Learning"),
        ("Proc. IEEE Conf. Computer Vision and Pattern Recognition",
         "Annual Meeting of the Association for Computational Linguistics"),
        ("", "Nature"),
    ],
)
def test_publicaciones_distintas_no_coinciden(cita, registro):
    assert not journals_match(cita, registro)


# ── Desempate por año y revista cuando varios registros encajan ─────────────


class _Resp:
    status_code = 200

    def __init__(self, data):
        self._d = data

    def json(self):
        return self._d


def _item(doi, titulo, familias, anio, revista):
    return {"DOI": doi, "title": [titulo], "type": "journal-article",
            "author": [{"family": f} for f in familias],
            "issued": {"date-parts": [[anio]]}, "container-title": [revista]}


async def _nosleep(_):
    pass


def _buscar(fuente, items):
    async def fetch(url, *, params=None, headers=None, timeout=10.0):
        return _Resp({"message": {"items": items}, "results": []})

    return asyncio.run(check_reference_existence([fuente], ResolverConfig(), fetch=fetch, sleep=_nosleep))


WATSON = _item("10.1038/171737a0", "Molecular structure of nucleic acids", ["Watson", "Crick"], 1953, "Nature")
OTRA = _item("10.1038/248765a0", "Molecular structure of nucleic acids", ["Watson", "Crick"], 1974, "Nature")


def test_dos_registros_plausibles_se_desempatan_por_el_anio():
    fuente = {"title": "Molecular structure of nucleic acids", "authors": "Watson, J. D., Crick, F. H. C.",
              "year": "1953", "journal": "Nature", "doi": ""}
    res, enriquecidas = _buscar(fuente, [WATSON, OTRA])
    assert res.status is CriterionStatus.PASSED
    assert enriquecidas[0]["doi"] == "10.1038/171737a0"


def test_sin_anio_que_desempate_sigue_siendo_no_verificada():
    fuente = {"title": "Molecular structure of nucleic acids", "authors": "Watson, Crick",
              "year": "", "journal": "", "doi": ""}
    res, _ = _buscar(fuente, [WATSON, OTRA])
    assert res.status is CriterionStatus.NOT_VERIFIED and "varios candidatos" in res.evidence[0]["reason"]


def test_si_ningun_candidato_coincide_en_anio_no_se_elige_ninguno():
    fuente = {"title": "Molecular structure of nucleic acids", "authors": "Watson, Crick",
              "year": "1999", "journal": "Nature", "doi": ""}
    res, _ = _buscar(fuente, [WATSON, OTRA])
    assert res.status is CriterionStatus.NOT_VERIFIED


# ── El conjunto de medición y el resumen del script ─────────────────────────


def _script():
    spec = importlib.util.spec_from_file_location("medir", REPO / "scripts" / "measure_reference_resolution.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_conjunto_tiene_validas_con_doi_sin_doi_y_controles_negativos():
    filas = _script().cargar()
    tipos = {f["kind"] for f in filas}
    assert {"valid_with_doi", "valid_without_doi", "fabricated", "altered"} <= tipos
    assert len({f["id"] for f in filas}) == len(filas)
    con_doi = [f for f in filas if f["kind"] == "valid_with_doi"]
    assert len(con_doi) >= 20 and all(f["doi"].startswith("10.") for f in con_doi)
    assert all(f["expect"] == "block" for f in filas if f["kind"] in ("fabricated", "altered"))
    assert all(f["expect"] == "pass" for f in filas if f["kind"].startswith("valid"))


def test_el_resumen_exige_el_90_por_ciento_y_cero_falsas_aceptaciones():
    medir = _script()

    def fila(kind, expect, outcome, i):
        return {"id": f"{kind}-{i}", "kind": kind, "expect": expect, "outcome": outcome, "reason": ""}

    ok = [fila("valid_with_doi", "pass", "passed", i) for i in range(18)] + [
        fila("valid_with_doi", "pass", "failed", i) for i in range(2)]
    negativos = [fila("fabricated", "block", "failed", 0)]
    r = medir.resumir(ok + negativos)
    assert r["con_doi"]["tasa"] == 0.9 and r["cumple_objetivo"]

    cae = ok[:17] + [fila("valid_with_doi", "pass", "failed", i) for i in range(3)]
    assert not medir.resumir(cae + negativos)["cumple_objetivo"]

    # Una sola falsa aceptación invalida el resultado aunque la tasa sea del 100 %.
    todo_ok = [fila("valid_with_doi", "pass", "passed", i) for i in range(20)]
    colado = [fila("altered", "block", "passed", 0)]
    r = medir.resumir(todo_ok + colado)
    assert r["falsas_aceptaciones"] == ["altered-0"] and not r["cumple_objetivo"]


def test_la_logica_del_script_de_postgres_detecta_lo_que_falta():
    spec = importlib.util.spec_from_file_location("pg", REPO / "scripts" / "verify_postgres_schema.py")
    pg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pg)
    completo = (pg.ESPERADO_ENUM, pg.COLUMNAS_ARTICULO, pg.COLUMNAS_INFORME,
                {"fk_articles_responsible_author_id_users", "fk_articles_approved_by_users"})
    assert pg.problemas(*completo) == []
    sin_etiqueta = (pg.ESPERADO_ENUM - {"REQUIRES_HUMAN_REVIEW"},) + completo[1:]
    assert "REQUIRES_HUMAN_REVIEW" in pg.problemas(*sin_etiqueta)[0]
    assert pg.dsn("postgresql+asyncpg://u:p@h/db") == "postgresql://u:p@h/db"
