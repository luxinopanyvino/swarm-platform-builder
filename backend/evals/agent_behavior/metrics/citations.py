"""Fidelidad de citas: lo citado existe en el corpus (SPEC-014 / T9.3).

Es la métrica que da sentido al RAG. Un agente que redacta bien pero se inventa
las fuentes no es un agente que falla poco: es peor que uno que no cita, porque
su salida **parece** verificable. Y es justo lo que un cambio de `prompt_template`
puede romper sin que nadie lo note leyendo el artículo.

Determinista a propósito: comprueba contra el corpus declarado del caso, no
contra el juicio de otro modelo.
"""
from __future__ import annotations

import re

from evals.agent_behavior.metrics import Metric, register, skipped
from evals.agent_behavior.models import CaseResult, EvalCase, MetricResult

NOMBRE = "citation_fidelity"

#: Citas en el texto: `[Fuente: X]` es el formato que produce el investigador, y
#: `(Autor, Año)` / `[1]` los de los estilos científicos del formateador.
_MARCADOR_FUENTE = re.compile(r"\[Fuente:\s*([^\]]+)\]")


def _titulos_del_corpus(caso: EvalCase) -> set[str]:
    titulos = set()
    for documento in caso.corpus:
        for clave in ("doc_title", "title", "filename"):
            valor = str(documento.get(clave) or "").strip()
            if valor:
                titulos.add(valor.lower())
    return titulos


def _evaluar(caso: EvalCase, resultado: CaseResult) -> MetricResult:
    citas = [c.strip() for c in _MARCADOR_FUENTE.findall(resultado.output or "")]
    if not citas:
        # No citar no es alucinar. Si el caso **exige** citas, lo dice en
        # `expect.min_citations` y entonces sí es un fallo.
        minimo = int(caso.expect.get("min_citations") or 0)
        if minimo > 0:
            return MetricResult(
                name=NOMBRE, score=0.0, passed=False,
                detail=f"el caso exige al menos {minimo} cita(s) y no hay ninguna",
            )
        return skipped(NOMBRE, "la salida no cita ninguna fuente")

    conocidas = _titulos_del_corpus(caso)
    inventadas = [cita for cita in citas if cita.lower() not in conocidas]
    fidelidad = 100.0 * (len(citas) - len(inventadas)) / len(citas)

    if inventadas:
        detalle = (
            f"{len(inventadas)} de {len(citas)} cita(s) no están en el corpus: "
            + ", ".join(sorted(inventadas)[:5])
        )
    else:
        detalle = f"las {len(citas)} cita(s) existen en el corpus"

    umbral = float(caso.expect.get("min_citation_fidelity", 100.0))
    return MetricResult(
        name=NOMBRE, score=round(fidelidad, 2), passed=fidelidad >= umbral, detail=detalle,
    )


register(Metric(
    name=NOMBRE,
    description="Porcentaje de citas de la salida que existen en el corpus del caso.",
    run=_evaluar,
    # Sin corpus no hay contra qué comprobar: la métrica no aplica.
    applies_to=lambda caso: bool(caso.corpus),
))
