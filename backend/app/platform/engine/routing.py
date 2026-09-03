"""Enrutado del grafo **como datos** (SPEC-013 / T8.3 / ADR-0005).

Antes, el bucle de revisión estaba escrito en el código del orquestador: la
condición miraba `if node_name == "revisor"`, el destino del rechazo era la
cadena `"redactor"`, y el umbral y el máximo de vueltas eran constantes de módulo.
Eso funciona mientras el único proyecto sea AlejandrIA. En una plataforma donde
cada proyecto trae sus propios agentes, un revisor que se llame `qa` o `editor`
no tiene bucle, y nadie se entera: el grafo se compila igual y el flujo
simplemente sigue recto.

Aquí el bucle es un **dato** (`ReviewLoop`) y el enrutador se fabrica a partir de
él, así que un proyecto puede declarar el suyo —o ninguno— sin tocar el motor.
T8.4 lo leerá del `template.yaml`; de momento lo declara el proyecto en Python.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Sequence, Tuple

logger = logging.getLogger(__name__)

FIN = "__end__"


@dataclass(frozen=True)
class ReviewLoop:
    """Un nodo que evalúa y puede devolver el flujo a un nodo anterior.

    Attributes:
        reviewer: nodo que emite la evaluación.
        on_reject: nodo al que se vuelve cuando la evaluación no llega al umbral.
        threshold: puntuación mínima para avanzar (`approval_score` del estado).
        max_loops: vueltas automáticas antes de avanzar de todos modos. Sin este
            tope, un revisor severo deja el pipeline dando vueltas para siempre.
        retry_targets: candidatos, en orden, a los que volver cuando la persona
            usuaria decide **añadir una fuente**. Se elige el primero que esté en
            el flujo; si no hay ninguno, se avanza.
    """

    reviewer: str
    on_reject: str
    threshold: float = 80.0
    max_loops: int = 3
    retry_targets: Tuple[str, ...] = field(default_factory=tuple)


def next_after(flow: Sequence[str], node: str) -> str:
    """Nodo que sigue a `node` en el flujo, o el final."""
    try:
        indice = list(flow).index(node)
    except ValueError:
        return FIN
    if indice + 1 < len(flow):
        return flow[indice + 1]
    return FIN


def make_review_router(loop: ReviewLoop) -> Callable[[Dict[str, Any]], str]:
    """Construye la arista condicional que sale de `loop.reviewer`.

    Tres caminos, en este orden de precedencia:

    1. **Decisión humana** (`user_decision`). Manda sobre la puntuación: si
       alguien ha mirado el borrador y ha dicho qué hacer, el umbral automático
       ya no tiene voz.
    2. **Puntuación por debajo del umbral** y quedan vueltas → se vuelve a
       `on_reject`.
    3. En cualquier otro caso, el siguiente nodo del flujo.
    """

    def router(state: Dict[str, Any]) -> str:
        flow = list(state.get("flow_sequence") or [])
        decision = state.get("user_decision")

        if decision == "add_source":
            for candidato in loop.retry_targets:
                if candidato in flow:
                    logger.info(
                        "Se añadió una fuente — volviendo a '%s' desde '%s'.",
                        candidato, loop.reviewer,
                    )
                    return candidato
            return next_after(flow, loop.reviewer)

        if decision == "continue":
            logger.info("Continuar con el borrador actual (decisión humana).")
            return next_after(flow, loop.reviewer)

        score = state.get("approval_score", 100)
        vueltas = state.get("loop_count", 0)
        if score < loop.threshold and vueltas < loop.max_loops:
            logger.info(
                "'%s' puntuó %s (vuelta %s/%s). Volviendo a '%s'.",
                loop.reviewer, score, vueltas, loop.max_loops, loop.on_reject,
            )
            return loop.on_reject

        siguiente = next_after(flow, loop.reviewer)
        logger.info("'%s' puntuó %s. Avanzando a '%s'.", loop.reviewer, score, siguiente)
        return siguiente

    return router
