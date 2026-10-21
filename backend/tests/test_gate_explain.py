"""Evidencia por criterio y acciones sugeridas del informe de la compuerta (#468)."""
from app.platform.publication_gate.explain import MAX_ITEMS, explain
from app.platform.publication_gate.types import CriterionResult, CriterionStatus

PASSED, FAILED = CriterionStatus.PASSED, CriterionStatus.FAILED
SECCIONES = ("introduction", "methods", "results", "discussion", "references")
FUENTES = [
    {"title": "Uno", "doi": "10.1/a", "year": "2020", "journal": "J"},
    {"title": "Dos", "doi": "", "year": "2021", "journal": "K"},
    {"title": "Síntesis", "url": "synthesis://llm"},
]


def _run(criteria, responsible=None, sources=FUENTES):
    return explain(criteria, sources, SECCIONES, responsible or {})


def test_un_criterio_superado_lista_lo_que_resolvio_y_no_propone_acciones():
    r = _run([CriterionResult("reference_existence", PASSED)])["reference_existence"]
    assert r["summary"]["total"] == 2 and r["summary"]["ok"] == 2  # la síntesis no cuenta
    assert [i["title"] for i in r["summary"]["items"]] == ["Uno", "Dos"]
    assert r["actions"] == []


def test_las_referencias_que_fallan_no_se_listan_como_buenas():
    c = CriterionResult("reference_existence", FAILED, [{"index": 2, "title": "Dos", "reason": "x"}])
    r = _run([c], {"reference_existence": "investigador"})["reference_existence"]
    assert r["summary"]["total"] == 2 and r["summary"]["ok"] == 1
    assert "items" not in r["summary"]
    assert [a["action"] for a in r["actions"]] == ["provide_doi", "rerun_agent"]
    assert r["actions"][0]["targets"] == [2]
    assert r["actions"][1]["agent"] == "investigador"


def test_estructura_incumplida_propone_reejecutar_y_editar():
    c = CriterionResult("imrad_structure", FAILED, [{"section": "references", "problem": "missing"}])
    r = _run([c], {"imrad_structure": "redactor"})["imrad_structure"]
    assert r["summary"]["problems"] == ["missing"]
    assert [a["action"] for a in r["actions"]] == ["rerun_agent", "edit_text"]


def test_sin_agente_responsable_solo_se_propone_editar():
    c = CriterionResult("placeholders", FAILED, [{"pattern": "TODO", "line": 1, "column": 1}])
    r = _run([c])["placeholders"]
    assert r["summary"] == {"code": "placeholders", "found": 1}
    assert r["actions"] == [{"action": "edit_text"}]


def test_estructura_superada_dice_que_secciones_se_comprobaron():
    r = _run([CriterionResult("imrad_structure", PASSED)])["imrad_structure"]
    assert r["summary"]["sections"] == list(SECCIONES) and r["actions"] == []


def test_un_criterio_no_verificado_tambien_propone_acciones():
    c = CriterionResult("imrad_structure", CriterionStatus.NOT_VERIFIED, [{"problem": "no_structure_declared"}])
    assert _run([c], {"imrad_structure": "redactor"})["imrad_structure"]["actions"]


def test_el_listado_de_evidencia_tiene_tope():
    muchas = [{"title": str(i), "doi": f"10.1/{i}"} for i in range(MAX_ITEMS + 10)]
    r = _run([CriterionResult("reference_existence", PASSED)], sources=muchas)["reference_existence"]
    assert r["summary"]["ok"] == MAX_ITEMS + 10 and len(r["summary"]["items"]) == MAX_ITEMS
