"""Presupuesto de tokens y latencia por agente (SPEC-014 / T9.3).

El coste de un agente es parte de su comportamiento. Un cambio de prompt que
mejora la redacción y triplica los tokens no es gratis, y sin una métrica que lo
mire, la regresión aparece en la factura o en el tiempo de espera y no en la PR
que la causó.

Se puntúa con margen y no con un aprobado/suspenso: consumir el 60% del
presupuesto y consumir el 99% no son lo mismo aunque los dos «pasen», y ver la
diferencia bajar a lo largo de varias PRs es justo lo que se quiere.
"""
from __future__ import annotations

from evals.agent_behavior.metrics import Metric, register, skipped
from evals.agent_behavior.models import CaseResult, EvalCase, MetricResult

NOMBRE = "budget"


def _puntuar(consumido: float, presupuesto: float) -> float:
    """100 sin consumir nada, 0 al doblar el presupuesto; lineal en medio."""
    if presupuesto <= 0:
        return 100.0
    exceso = consumido / presupuesto
    return max(0.0, min(100.0, 100.0 * (2.0 - exceso) / 1.0)) if exceso > 1.0 else \
        round(100.0 - 50.0 * exceso, 2)


def _evaluar(caso: EvalCase, resultado: CaseResult) -> MetricResult:
    limites = {
        "tokens_out": caso.expect.get("max_tokens_out"),
        "tokens_in": caso.expect.get("max_tokens_in"),
        "latency_ms": caso.expect.get("max_latency_ms"),
    }
    medidos = {
        "tokens_out": resultado.tokens_out,
        "tokens_in": resultado.tokens_in,
        "latency_ms": resultado.latency_ms,
    }

    declarados = {k: float(v) for k, v in limites.items() if v}
    if not declarados:
        return skipped(NOMBRE, "el caso no declara presupuesto")

    # En modo `replay` la latencia es la de reproducir un fichero, no la del
    # agente: medirla sería inventarse un número.
    if resultado.latency_ms <= 0 and set(declarados) == {"latency_ms"}:
        return skipped(NOMBRE, "sin latencia medida en esta ejecución")

    puntuaciones = []
    excedidos = []
    for clave, presupuesto in declarados.items():
        consumido = float(medidos[clave] or 0)
        if clave == "latency_ms" and consumido <= 0:
            continue
        puntuaciones.append(_puntuar(consumido, presupuesto))
        if consumido > presupuesto:
            excedidos.append(f"{clave}={consumido:.0f} > {presupuesto:.0f}")

    if not puntuaciones:
        return skipped(NOMBRE, "sin nada medido que comparar con el presupuesto")

    puntuacion = round(sum(puntuaciones) / len(puntuaciones), 2)
    detalle = "dentro del presupuesto" if not excedidos else "excedido: " + ", ".join(excedidos)
    return MetricResult(
        name=NOMBRE, score=puntuacion, passed=not excedidos, detail=detalle,
    )


register(Metric(
    name=NOMBRE,
    description="Margen respecto al presupuesto de tokens y latencia declarado por el caso.",
    run=_evaluar,
    applies_to=lambda caso: any(
        caso.expect.get(clave) for clave in ("max_tokens_out", "max_tokens_in", "max_latency_ms")
    ),
))
