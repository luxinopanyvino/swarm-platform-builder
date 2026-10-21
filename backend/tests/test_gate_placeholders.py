"""SPEC-032 AC1 / T20.1 — detector de marcadores de posición (PR-REG-01)."""
import pytest

from app.platform.publication_gate import CriterionStatus
from app.platform.publication_gate.placeholders import (
    DEFAULT_PLACEHOLDERS,
    check_placeholders,
)


def test_texto_limpio_pasa():
    r = check_placeholders("Los resultados muestran un efecto (García, 2021).")
    assert r.status is CriterionStatus.PASSED and not r.blocking and r.evidence == []


@pytest.mark.parametrize("marker", DEFAULT_PLACEHOLDERS)
def test_cada_marcador_bloquea_y_se_nombra(marker):
    r = check_placeholders(f"Primera línea.\nAntes {marker} después.")
    assert r.status is CriterionStatus.FAILED and r.blocking
    assert r.evidence[0]["pattern"] == marker
    assert r.evidence[0]["line"] == 2


def test_posicion_exacta():
    text = "abc [?] def"
    r = check_placeholders(text)
    assert text[r.evidence[0]["offset"] :].startswith("[?]")
    assert r.evidence[0]["column"] == 5


def test_codigo_delimitado_se_ignora():
    text = "Texto.\n```\n(Author, Year) y TODO\n```\nFin."
    assert check_placeholders(text).status is CriterionStatus.PASSED


def test_codigo_en_linea_se_ignora_pero_no_el_resto():
    text = "Cita el marcador `(Author, Year)` y aquí otro (Author, Year)."
    r = check_placeholders(text)
    assert len(r.evidence) == 1 and r.evidence[0]["offset"] > text.index("aquí")


def test_posiciones_se_conservan_tras_ignorar_codigo():
    text = "```\nx\n```\nTODO"
    assert check_placeholders(text).evidence[0]["line"] == 4


def test_valla_sin_cerrar_ignora_hasta_el_final():
    assert check_placeholders("```\nTODO sin cerrar").status is CriterionStatus.PASSED


def test_palabras_solo_enteras_y_en_mayusculas():
    for ok in ("todo el mundo", "TODOS los casos", "MAXXXIMO", "Todo"):
        assert check_placeholders(ok).status is CriterionStatus.PASSED, ok


def test_marcadores_con_corchetes_ignoran_mayusculas():
    assert check_placeholders("Dato [Citation Needed].").blocking


def test_lista_configurable():
    assert check_placeholders("FIXME", markers=["FIXME"]).blocking
    assert not check_placeholders("TODO", markers=["FIXME"]).blocking


def test_texto_vacio_o_nulo():
    assert check_placeholders("").status is CriterionStatus.PASSED
    assert check_placeholders(None).status is CriterionStatus.PASSED
