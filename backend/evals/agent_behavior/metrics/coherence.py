"""Coherencia del texto, juzgada por un modelo (SPEC-014 / T9.4 / AC4).

Es la única métrica del harness que no se puede calcular con una expresión
regular. Un texto puede citar fuentes que existen, cumplir el formato APA y caber
en el presupuesto, y aun así contradecirse entre la metodología y los resultados.
Las tres métricas deterministas lo darían por bueno.

El juicio lo produce el **juez** (`judge.py`) y llega ya hecho en
`resultado.judgement`: esta métrica solo lo puntúa. Ese reparto es deliberado —
la métrica sigue siendo una función pura, y la llamada al modelo ocurre donde se
sabe el modo, así que en `replay` no se llama a nadie.

**Sin veredicto, la métrica se salta con motivo.** La alternativa —puntuar 100
porque no se ha mirado— es la mentira con buena nota que este harness existe para
no contar; y puntuar 0 sería peor, porque haría fallar el gate por una evaluación
que no se llegó a hacer.
"""
from __future__ import annotations

from evals.agent_behavior.metrics import Metric, register, skipped
from evals.agent_behavior.models import CaseResult, EvalCase, MetricResult

NOMBRE = "coherence"


def _evaluar(caso: EvalCase, resultado: CaseResult) -> MetricResult:
    veredicto = resultado.judgement
    if not veredicto:
        return skipped(
            NOMBRE,
            "sin veredicto del juez: grábalo en el caso (`recorded_judgement`) "
            "o ejecuta en modo live",
        )

    puntuacion = float(veredicto.get("score") or 0.0)
    minimo = float(caso.expect["min_coherence"])
    motivo = str(veredicto.get("reason") or "").strip()

    detalle = f"el juez puntúa {puntuacion:.0f}/100 (mínimo {minimo:.0f})"
    if motivo:
        detalle += f" — {motivo}"

    return MetricResult(
        name=NOMBRE, score=round(puntuacion, 2), passed=puntuacion >= minimo, detail=detalle,
    )


register(Metric(
    name=NOMBRE,
    description="Coherencia interna del texto según un juez con rúbrica fija (modelo de la plataforma).",
    run=_evaluar,
    applies_to=lambda caso: "min_coherence" in (caso.expect or {}),
))
