"""Calibración del score del revisor (SPEC-014 / T9.4 / AC4).

El revisor no escribe: **decide**. Puntúa el borrador de 0 a 100 y, con el umbral
de 80, esa cifra decide si el pipeline vuelve al redactor. Que sea un número no
lo hace objetivo: un revisor que aprueba todo con 85 y otro que suspende todo con
70 producen los dos un número perfectamente formado, y los dos rompen el
pipeline — el primero deja pasar basura, el segundo agota el bucle en textos
buenos.

Lo que mide esta métrica es la **distancia a una referencia humana**
(`expect.reference_score`), no si el score es alto. Un caso escrito para que
suspenda tiene que suspender: acertar en un borrador flojo puntúa igual de bien
que acertar en uno bueno.

Y mide algo más, que es lo que de verdad rompe: **el lado del umbral**. Un 78
frente a una referencia de 82 son cuatro puntos, pero es la diferencia entre
seguir y reescribir. Cruzar el umbral se penaliza aparte de la distancia.
"""
from __future__ import annotations

from evals.agent_behavior.metrics import Metric, register
from evals.agent_behavior.models import CaseResult, EvalCase, MetricResult

NOMBRE = "reviewer_calibration"

#: El mismo que aplica el revisor en producción (`adapters/revisor.py`): por
#: debajo, el borrador vuelve al redactor. Si allí cambia, aquí también.
UMBRAL_APROBACION = 80.0

#: Cuánta desviación se tolera antes de puntuar 0. 40 puntos de 100 es media
#: escala: más allá, el revisor no está calibrado, está opinando otra cosa.
DESVIACION_MAXIMA = 40.0


def _lado(score: float) -> str:
    return "aprueba" if score >= UMBRAL_APROBACION else "rechaza"


def _evaluar(caso: EvalCase, resultado: CaseResult) -> MetricResult:
    decision = resultado.decision or {}
    obtenido = decision.get("score")
    if obtenido is None:
        return MetricResult(
            name=NOMBRE, score=0.0, passed=False,
            detail="el revisor no devolvió 'approval_score': sin decisión no hay nada que calibrar",
        )

    referencia = float(caso.expect["reference_score"])
    obtenido = float(obtenido)
    desviacion = abs(obtenido - referencia)

    cercania = max(0.0, 100.0 * (1 - desviacion / DESVIACION_MAXIMA))
    mismo_lado = _lado(obtenido) == _lado(referencia)

    # Cruzar el umbral no es un error de grado: cambia lo que hace el pipeline.
    # Se penaliza a la mitad para que un acierto de lado con desviación grande no
    # puntúe como uno ajustado, y para que un fallo de lado no pueda aprobar por
    # los pelos.
    puntuacion = cercania if mismo_lado else cercania / 2

    tolerancia = float(caso.expect.get("max_score_deviation", 15.0))
    pasa = mismo_lado and desviacion <= tolerancia

    if not mismo_lado:
        detalle = (
            f"cruza el umbral de {UMBRAL_APROBACION:.0f}: {_lado(obtenido)} con "
            f"{obtenido:.0f} cuando la referencia {_lado(referencia)} con {referencia:.0f}"
        )
    elif desviacion > tolerancia:
        detalle = (
            f"se desvía {desviacion:.0f} puntos de la referencia "
            f"({obtenido:.0f} vs {referencia:.0f}); se toleran {tolerancia:.0f}"
        )
    else:
        detalle = f"{obtenido:.0f} frente a una referencia de {referencia:.0f}"

    return MetricResult(
        name=NOMBRE, score=round(puntuacion, 2), passed=pasa, detail=detalle,
    )


register(Metric(
    name=NOMBRE,
    description="Distancia del score del revisor a una referencia humana, y si cae del mismo lado del umbral.",
    run=_evaluar,
    # Sin referencia no hay contra qué calibrar. La declara el caso, así que solo
    # se aplica a los casos escritos para eso.
    applies_to=lambda caso: "reference_score" in (caso.expect or {}),
))
