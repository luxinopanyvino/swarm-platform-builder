"""SPEC-032 AC12 / T20.15 — la evaluación EDD cubre lo que cambia SPEC-032."""
import asyncio

import yaml
from pathlib import Path

from evals.agent_behavior import loader, metrics
from evals.agent_behavior.models import CaseResult, EvalCase
from evals.agent_behavior.metrics.reference_completeness import referencias

RAIZ = Path(__file__).resolve().parents[1] / "evals" / "agent_behavior"


def _caso(**expect):
    return EvalCase(id="c", agent="formateador", input={}, expect=expect)


def _resultado(texto):
    return CaseResult(case_id="c", agent="formateador", output=texto)


def _evaluar(texto, **expect):
    return metrics.get("reference_completeness").run(
        _caso(complete_references=True, **expect), _resultado(texto))


# ── La métrica ──────────────────────────────────────────────────────────────


def test_referencias_completas_puntuan_100():
    texto = "## Referencias\n[1] A. B., \"T,\" 2020. https://doi.org/10.1/x\n[2] C. D., \"U,\" 2019. doi: 10.2/y\n"
    r = _evaluar(texto)
    assert r.passed and r.score == 100.0


def test_un_nombre_de_archivo_o_una_referencia_sin_anio_o_sin_identificador_falla():
    texto = "## Referencias\n[1] informe-final.pdf\n[2] A. B., \"T,\" 2020.\n[3] C. D., \"U,\" https://x.org/u\n[4] E. F., \"V,\" 2018. https://doi.org/10.1/v\n"
    r = _evaluar(texto)
    assert not r.passed and r.score == 25.0
    assert "informe-final.pdf" in r.detail and "sin año ni identificador" in r.detail
    assert "sin identificador" in r.detail and "sin año" in r.detail


def test_sin_seccion_de_referencias_no_se_da_por_buena():
    r = _evaluar("Un texto sin bibliografía.")
    assert not r.passed and r.score == 0.0


def test_solo_aplica_a_los_casos_que_la_exigen():
    m = metrics.get("reference_completeness")
    assert not m.applies_to(_caso(scientific_format="ieee"))
    assert m.applies_to(_caso(complete_references=True))


def test_usa_la_ultima_seccion_de_referencias():
    assert referencias("## Referencias\nuna\n\n## Referencias\n[1] dos 2020 https://x.org") == [
        "[1] dos 2020 https://x.org"]


# ── Los datasets ────────────────────────────────────────────────────────────


def test_el_golden_del_formateador_exige_referencias_completas_y_las_cumple():
    from evals.agent_behavior import runner

    informe = asyncio.run(runner.run("formateador-golden", mode="replay"))
    caso = informe.cases[0]
    nombres = {m.name: m for m in caso.metrics}
    assert nombres["reference_completeness"].passed and not nombres["reference_completeness"].skipped_reason


def test_la_regresion_de_referencia_incompleta_la_detecta_solo_esta_metrica():
    from evals.agent_behavior import runner

    informe = asyncio.run(runner.run("formateador-regressions", mode="replay"))
    por_id = {c.case_id: {m.name for m in c.metrics if not m.passed} for c in informe.cases}
    # La regresión antigua (IEEE degradado) sigue detectándose como antes…
    assert "format_compliance" in por_id["ieee-degradado"]
    # …y la nueva no la ve la métrica de formato, solo la de completitud.
    assert por_id["referencia-incompleta-impresa"] == {"reference_completeness"}


def test_el_revisor_sin_veredicto_sigue_documentado_como_regresion():
    from evals.agent_behavior import runner

    informe = asyncio.run(runner.run("revisor-regressions", mode="replay"))
    fallos = {c.case_id: {m.name for m in c.metrics if not m.passed} for c in informe.cases}
    assert fallos["revisor-sin-veredicto"] == {"reviewer_calibration"}


def test_el_redactor_golden_pide_resultados_y_discusion_por_separado():
    ds = loader.load_by_id("redactor-golden")
    secciones = ds.cases[0].expect["required_sections"]
    assert "Resultados" in secciones and "Discusión" in secciones


def test_los_umbrales_declaran_la_metrica_nueva_y_su_dataset_la_computa():
    umbrales = yaml.safe_load((RAIZ / "thresholds.yaml").read_text(encoding="utf-8"))
    assert "reference_completeness" in umbrales["agents"]["formateador"]["metrics"]
    assert umbrales["enforce"] is False  # los golden siguen siendo `handwritten`
