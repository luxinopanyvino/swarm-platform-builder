"""SPEC-032 AC2 / T20.2 — estructura de referencias (PR-REG-02)."""
import asyncio

from app.modules.agents.adapters.formateador import run_formateador
from app.platform.publication_gate import CriterionStatus
from app.platform.publication_gate.references import (
    check_reference_structure,
    missing_fields,
)

COMPLETA = {
    "title": "Attention is all you need",
    "authors": "Vaswani, A.",
    "year": "2017",
    "journal": "NeurIPS",
    "doi": "10.5555/3295222.3295349",
}


def test_fuente_completa_pasa():
    r = check_reference_structure([COMPLETA])
    assert r.status is CriterionStatus.PASSED and not r.blocking


def test_solo_nombre_de_archivo_bloquea_y_dice_que_falta():
    # Lo que produce hoy el Investigador con un PDF subido al RAG.
    fuente = {"title": "informe-final", "filename": "informe-final.pdf",
              "authors": "", "journal": "", "year": "", "doi": "", "url": ""}
    r = check_reference_structure([fuente])
    assert r.blocking
    assert r.evidence[0]["missing"] == ["identifier", "authors", "year", "journal"]


def test_cada_campo_ausente_se_nombra():
    for campo, clave in [("authors", "authors"), ("year", "year"), ("journal", "journal")]:
        f = {**COMPLETA, clave: ""}
        assert missing_fields(f) == [campo]
    assert missing_fields({**COMPLETA, "doi": ""}) == ["identifier"]


def test_url_http_basta_como_identificador_pero_no_las_internas():
    sin_doi = {**COMPLETA, "doi": ""}
    assert missing_fields({**sin_doi, "url": "https://example.org/p"}) == []
    assert missing_fields({**sin_doi, "url": "local://doc-1"}) == ["identifier"]


def test_valores_basura_cuentan_como_vacios():
    assert "year" in missing_fields({**COMPLETA, "year": "N/A"})


def test_sintesis_del_llm_no_se_evalua():
    r = check_reference_structure([COMPLETA, {"url": "synthesis://llm", "title": "x"}])
    assert r.status is CriterionStatus.PASSED


def test_sin_fuentes_pasa_esta_comprobacion():
    assert check_reference_structure([]).status is CriterionStatus.PASSED


def test_formateador_no_imprime_incompletas_y_las_informa():
    incompleta = {"title": "informe-final", "authors": "", "year": "", "journal": "", "doi": ""}
    state = {
        "draft_text": "Cuerpo del manuscrito.",
        "sources": [COMPLETA, incompleta],
        "scientific_format": "apa",
        "agent_settings": {},
    }
    import app.modules.agents.adapters.formateador as f

    async def sin_llm(*a, **k):
        raise RuntimeError("sin LLM en el test")

    original = f.call_llm
    f.call_llm = sin_llm
    try:
        out = asyncio.run(run_formateador(state))
    finally:
        f.call_llm = original
    assert "Attention is all you need" in out["formatted_text"]
    assert "informe-final" not in out["formatted_text"]
    assert out["reference_issues"][0]["title"] == "informe-final"
    assert "identifier" in out["reference_issues"][0]["missing"]
