"""Conjuntos golden y métricas asistidas (SPEC-014 / T9.4 / AC4).

AC4 pide **dos cosas**: datasets *golden* versionados en el repo, y que se
computen cinco métricas de comportamiento. T9.3 dejó tres —fidelidad de citas,
cumplimiento de formato y presupuesto—; aquí llegan las dos que faltan, que son
precisamente las que no se pueden calcular con una expresión regular:

* **calibración del revisor** frente a una referencia. El revisor no escribe:
  decide, y su score cruza el umbral de 80 que hace volver el borrador al
  redactor. Un revisor descalibrado produce un número perfectamente formado y
  rompe el pipeline igual.
* **coherencia**, juzgada por un modelo de la plataforma con rúbrica fija. Es la
  única que caza un texto que cita bien, cumple APA, cabe en el presupuesto y se
  contradice a sí mismo.

Lo que más fácil se hace mal aquí es el reparto: si la métrica llamara al juez,
`replay` dejaría de ser reproducible y la CI de T9.5 pasaría a depender de que
haya un modelo. El juez lo pide el runner, donde se sabe el modo.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_edd_golden.db")

from evals.agent_behavior import judge as jueces  # noqa: E402
from evals.agent_behavior import loader, metrics, providers, report, runner  # noqa: E402
from evals.agent_behavior.models import CaseResult, EvalCase  # noqa: E402

DATASETS = ROOT_DIR / "evals" / "agent_behavior" / "datasets"

#: Los cuatro agentes de AlejandrIA que producen algo evaluable. El publicador
#: no: publica, no genera texto ni decide.
AGENTES = ("investigador", "redactor", "revisor", "formateador")


# ── Los conjuntos golden ────────────────────────────────────────────────────

@pytest.mark.parametrize("agente", AGENTES)
def test_cada_agente_tiene_su_conjunto_golden(agente):
    """AC4 pide datasets golden *versionados en el repo*, no un ejemplo."""
    dataset = loader.load_by_id(f"{agente}-golden")
    assert dataset.cases, f"{agente}-golden no tiene casos"
    assert all(caso.agent == agente for caso in dataset.cases)
    assert dataset.version


@pytest.mark.parametrize("agente", AGENTES)
@pytest.mark.asyncio
async def test_el_golden_pasa_entero_para_poder_ser_gate(agente):
    """Un conjunto de referencia con un caso que falla a propósito no sirve de
    línea base: T9.5 no podría distinguir «ha regresado» de «siempre fue rojo»."""
    informe = await runner.run(f"{agente}-golden", mode="replay")
    assert informe.passed, report.to_markdown(informe)


@pytest.mark.parametrize("agente", AGENTES)
@pytest.mark.asyncio
async def test_cada_agente_tiene_documentadas_sus_regresiones(agente):
    """Y fallan a propósito: son documentación ejecutable de qué se mide."""
    informe = await runner.run(f"{agente}-regressions", mode="replay")
    assert not informe.passed, "un dataset de regresiones que pasa no documenta nada"


def test_los_datasets_declaran_de_donde_salen_sus_salidas():
    """Un `replay` sobre salidas escritas a mano evalúa la métrica, no al modelo.
    Es evidencia de otra cosa, y sin declararlo se leen como si fueran lo mismo."""
    for ruta in sorted(DATASETS.glob("*.jsonl")):
        dataset = loader.load(ruta)
        assert dataset.provenance in loader.PROCEDENCIAS, (
            f"{ruta.name} no declara 'provenance'"
        )


def test_el_informe_avisa_cuando_las_salidas_no_son_grabadas():
    """El mismo criterio que el aviso de `replay`: lo que no se puede deducir de
    un número tiene que estar escrito al lado."""
    import asyncio

    informe = asyncio.run(runner.run("revisor-golden", mode="replay"))
    markdown = report.to_markdown(informe)
    assert "handwritten" in markdown
    assert "no que el modelo se comporte así" in markdown
    assert informe.context.dataset_provenance == "handwritten"


# ── Calibración del revisor ─────────────────────────────────────────────────

def _caso_revisor(referencia, **expect):
    return EvalCase(
        id="c", agent="revisor",
        expect={"reference_score": referencia, **expect},
    )


def _resultado(score):
    return CaseResult(case_id="c", agent="revisor",
                      decision={"score": score, "coherent": score >= 80})


def _calibrar(referencia, score, **expect):
    return metrics.get("reviewer_calibration").run(
        _caso_revisor(referencia, **expect), _resultado(score)
    )


def test_un_score_cercano_a_la_referencia_puntua_alto():
    resultado = _calibrar(88, 86)
    assert resultado.passed
    assert resultado.score > 90


def test_cruzar_el_umbral_falla_aunque_la_distancia_sea_corta():
    """Cuatro puntos, pero es la diferencia entre seguir y reescribir: el bucle
    del pipeline se dispara por el lado del umbral, no por la distancia."""
    resultado = _calibrar(82, 78)
    assert not resultado.passed
    assert "umbral" in resultado.detail
    # Y puntúa por debajo de lo que puntuaría la misma distancia sin cruzarlo.
    assert resultado.score < _calibrar(88, 84).score


def test_un_revisor_complaciente_se_detecta():
    """Aprueba con 85 lo que la referencia rechaza con 62: deja pasar basura."""
    resultado = _calibrar(62, 85)
    assert not resultado.passed
    assert "aprueba" in resultado.detail and "rechaza" in resultado.detail


def test_un_revisor_severo_tambien():
    """Rechaza con 61 lo que la referencia aprueba con 88: agota el bucle en
    textos buenos, que es igual de roto y se nota menos."""
    resultado = _calibrar(88, 61)
    assert not resultado.passed


def test_una_desviacion_grande_del_mismo_lado_tampoco_pasa():
    """Acertar el lado por casualidad no es estar calibrado."""
    resultado = _calibrar(95, 81, max_score_deviation=10)
    assert not resultado.passed
    assert "se desvía" in resultado.detail


def test_sin_decision_la_calibracion_falla_en_vez_de_saltarse():
    """Que el revisor no devuelva score **es** el fallo: saltarla lo escondería."""
    resultado = metrics.get("reviewer_calibration").run(
        _caso_revisor(80), CaseResult(case_id="c", agent="revisor")
    )
    assert not resultado.passed
    assert "approval_score" in resultado.detail


def test_la_calibracion_no_aplica_a_quien_no_tiene_referencia():
    metrica = metrics.get("reviewer_calibration")
    assert not metrica.applies_to(EvalCase(id="c", agent="redactor"))
    assert metrica.applies_to(_caso_revisor(80))


# ── Coherencia y el juez ────────────────────────────────────────────────────

def _caso_coherencia(minimo=70):
    return EvalCase(id="c", agent="redactor", expect={"min_coherence": minimo})


def test_la_coherencia_puntua_el_veredicto_del_juez():
    resultado = metrics.get("coherence").run(
        _caso_coherencia(70),
        CaseResult(case_id="c", agent="redactor", output="texto",
                   judgement={"score": 88, "reason": "las secciones se conectan"}),
    )
    assert resultado.passed and resultado.score == 88
    assert "las secciones se conectan" in resultado.detail


def test_un_texto_que_se_contradice_no_pasa():
    resultado = metrics.get("coherence").run(
        _caso_coherencia(70),
        CaseResult(case_id="c", agent="redactor", output="texto",
                   judgement={"score": 22, "reason": "se contradice"}),
    )
    assert not resultado.passed


def test_sin_veredicto_la_coherencia_se_salta_con_motivo():
    """Ni 100 —aprobar por no haber mirado— ni 0 —hacer fallar el gate por una
    evaluación que no se hizo—."""
    resultado = metrics.get("coherence").run(
        _caso_coherencia(70), CaseResult(case_id="c", agent="redactor", output="texto"),
    )
    assert resultado.skipped_reason
    assert "live" in resultado.skipped_reason


@pytest.mark.asyncio
async def test_en_replay_el_juez_no_llama_a_ningun_modelo(monkeypatch):
    """Es lo que hace que la suite corra sin Ollama y que el gate de T9.5 sea
    determinista. Si la métrica llamara al juez por su cuenta, esto se rompería
    sin que ningún test lo notara."""
    import app.platform.llm as llm

    async def _prohibido(*_a, **_k):
        raise AssertionError("el modo replay ha llamado al modelo")

    monkeypatch.setattr(llm, "call_llm", _prohibido)
    informe = await runner.run("redactor-golden", mode="replay")
    assert informe.passed


def test_el_modo_live_construye_el_juez_de_la_plataforma():
    juez = jueces.build("live")
    assert juez.__class__.__name__ == "PlatformJudge"
    assert jueces.build("replay").__class__.__name__ == "RecordedJudge"
    with pytest.raises(ValueError):
        jueces.build("inventado")


def test_el_juez_solo_se_pide_cuando_el_caso_lo_declara():
    assert jueces.needs_judgement(_caso_coherencia())
    assert not jueces.needs_judgement(EvalCase(id="c", agent="redactor"))


def test_la_rubrica_no_juzga_lo_que_no_toca():
    """Una rúbrica que premie la extensión o el estilo deja de medir coherencia y
    pasa a medir otra cosa, y los números dejan de ser comparables entre PRs."""
    rubrica = jueces.RUBRICA.lower()
    assert "coherencia" in rubrica
    assert "no premies ni penalices la extensión" in rubrica
    # Y pide JSON: el veredicto tiene que ser parseable, no prosa.
    assert '"score"' in jueces.RUBRICA


@pytest.mark.asyncio
async def test_el_juez_de_la_plataforma_llama_con_temperature_cero(monkeypatch):
    """SPEC-014 §5: rúbrica fija y `temperature=0`. Un juez que cambia de criterio
    entre ejecuciones convierte el gate en un generador de rojos aleatorios."""
    import app.platform.llm as llm

    recibido = {}

    async def _falso(prompt, **kwargs):
        recibido.update(kwargs)
        recibido["prompt"] = prompt
        return '{"score": 77, "reason": "vale"}'

    monkeypatch.setattr(llm, "call_llm", _falso)
    veredicto = await jueces.PlatformJudge().assess(
        _caso_coherencia(), CaseResult(case_id="c", agent="redactor", output="un texto"),
    )
    assert recibido["temperature"] == 0
    assert "un texto" in recibido["prompt"]
    assert veredicto["score"] == 77
    assert veredicto["rubric_version"] == jueces.RUBRICA_VERSION


@pytest.mark.asyncio
async def test_el_juez_no_juzga_lo_que_no_hay(monkeypatch):
    """Sin texto no hay coherencia que medir; llamar al modelo con vacío gastaría
    tokens para que puntúe la nada."""
    import app.platform.llm as llm

    async def _prohibido(*_a, **_k):
        raise AssertionError("ha llamado al modelo con la salida vacía")

    monkeypatch.setattr(llm, "call_llm", _prohibido)
    assert await jueces.PlatformJudge().assess(
        _caso_coherencia(), CaseResult(case_id="c", agent="redactor", output="   "),
    ) is None


def test_un_veredicto_sin_json_se_rechaza():
    with pytest.raises(ValueError):
        jueces._parsear_veredicto("El texto me parece bastante coherente, la verdad.")


def test_un_veredicto_con_score_no_numerico_se_rechaza():
    with pytest.raises(ValueError):
        jueces._parsear_veredicto('{"score": "alto", "reason": "x"}')


def test_el_veredicto_se_recorta_al_rango():
    """Un modelo devuelve 120 de vez en cuando; propagarlo descuadraría la media."""
    assert jueces._parsear_veredicto('{"score": 120}')["score"] == 100.0
    assert jueces._parsear_veredicto('{"score": -5}')["score"] == 0.0


def test_el_juez_envuelto_en_prosa_se_parsea():
    """Es lo que hacen los modelos pequeños: JSON con explicación alrededor."""
    veredicto = jueces._parsear_veredicto(
        'Claro, aquí tienes:\n```json\n{"score": 64, "reason": "hay saltos"}\n```'
    )
    assert veredicto["score"] == 64.0


@pytest.mark.asyncio
async def test_un_juez_que_falla_no_tumba_el_caso(monkeypatch, capsys):
    """La métrica se saltará con motivo, que es más honesto que puntuar sin haber
    mirado; pero el fallo se avisa, no se traga."""
    class _JuezRoto:
        mode = "live"

        async def assess(self, caso, resultado):
            raise RuntimeError("el proveedor no responde")

    caso = EvalCase(id="c", agent="redactor", expect={"min_coherence": 70},
                    recorded_output="texto")
    resultado = await runner.evaluate_case(
        caso, providers.ReplayProvider(), None, _JuezRoto()
    )
    assert resultado.judgement is None
    coherencia = next(m for m in resultado.metrics if m.name == "coherence")
    assert coherencia.skipped_reason
    assert "el juez falló" in capsys.readouterr().err


# ── El revisor, que decide y no escribe ─────────────────────────────────────

@pytest.mark.asyncio
async def test_un_agente_que_decide_y_no_escribe_es_evaluable():
    """El revisor no produce texto: `output_text` no encuentra nada suyo. Si la
    decisión no llegara a la métrica, sería inevaluable y AC4 no se cumpliría."""
    caso = EvalCase(id="c", agent="revisor", expect={"reference_score": 80},
                    recorded_decision={"score": 82, "coherent": True})
    resultado = await runner.evaluate_case(caso, providers.ReplayProvider())
    assert resultado.error is None, resultado.error
    assert resultado.decision == {"score": 82, "coherent": True}
    calibracion = next(m for m in resultado.metrics if m.name == "reviewer_calibration")
    assert calibracion.passed


def test_la_decision_se_lee_por_el_mismo_sitio_que_la_traza():
    """Si el revisor cambia de forma, cambia en un sitio: el lector de T9.1."""
    fuente = (ROOT_DIR / "evals" / "agent_behavior" / "providers.py").read_text(encoding="utf-8")
    assert "explainability.decision_of" in fuente


def test_el_dataset_del_revisor_cubre_los_dos_lados_del_umbral():
    """Un conjunto que solo trae aprobados no detecta a un revisor complaciente."""
    dataset = loader.load_by_id("revisor-golden")
    referencias = [c.expect["reference_score"] for c in dataset.cases]
    assert any(r >= 80 for r in referencias), "ningún caso de aprobación"
    assert any(r < 80 for r in referencias), "ningún caso de rechazo"
