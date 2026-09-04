"""Cumplimiento estructural del formato científico (SPEC-014 / T9.3).

Comprueba lo que **se puede comprobar sin opinar**: que el estilo de cita pedido
aparece con su forma, y que están las secciones que el caso exige. No juzga si el
artículo está bien escrito —eso es trabajo del juez asistido, T9.4—; juzga si
cumple la estructura que se le pidió.

Vale la pena porque es exactamente lo que se rompe en silencio: cambiar el
`prompt_template` del formateador para mejorar la redacción y perder las citas
numeradas de IEEE no se nota leyendo por encima.
"""
from __future__ import annotations

import re

from evals.agent_behavior.metrics import Metric, register, skipped
from evals.agent_behavior.models import CaseResult, EvalCase, MetricResult

NOMBRE = "format_compliance"

#: Forma reconocible de cada estilo en el cuerpo del texto.
_PATRONES = {
    "apa": re.compile(r"\([^()]*\b(19|20)\d{2}[a-z]?\)"),          # (Autor, 2021)
    "chicago": re.compile(r"\([^()]*\b(19|20)\d{2}\)"),            # (Autor 2021)
    "ieee": re.compile(r"\[\d+\]"),                                # [1]
    "vancouver": re.compile(r"[\[(]\d+[\])]|\(\d+\)"),             # (1) o [1]
    "nature": re.compile(r"[\[(]\d+[\])]|\^\d+|<sup>\d+</sup>"),   # superíndices
}


def _evaluar(caso: EvalCase, resultado: CaseResult) -> MetricResult:
    estilo = str(caso.expect.get("scientific_format") or "").strip().lower()
    texto = resultado.output or ""

    comprobaciones: list[tuple[str, bool]] = []

    if estilo and estilo != "none":
        patron = _PATRONES.get(estilo)
        if patron is None:
            return skipped(NOMBRE, f"no hay patrón declarado para el estilo '{estilo}'")
        comprobaciones.append((f"citas en estilo {estilo.upper()}", bool(patron.search(texto))))

    for seccion in caso.expect.get("required_sections") or []:
        presente = re.search(rf"^#{{1,6}}\s*.*{re.escape(str(seccion))}", texto,
                             re.IGNORECASE | re.MULTILINE) is not None
        comprobaciones.append((f"sección «{seccion}»", presente))

    if not comprobaciones:
        return skipped(NOMBRE, "el caso no declara formato ni secciones exigidas")

    superadas = sum(1 for _, ok in comprobaciones if ok)
    puntuacion = 100.0 * superadas / len(comprobaciones)
    faltan = [nombre for nombre, ok in comprobaciones if not ok]
    detalle = (
        "cumple " + ", ".join(nombre for nombre, _ in comprobaciones)
        if not faltan else "falta: " + ", ".join(faltan)
    )

    umbral = float(caso.expect.get("min_format_compliance", 100.0))
    return MetricResult(
        name=NOMBRE, score=round(puntuacion, 2), passed=puntuacion >= umbral, detail=detalle,
    )


register(Metric(
    name=NOMBRE,
    description="Porcentaje de exigencias estructurales del caso que cumple la salida.",
    run=_evaluar,
    applies_to=lambda caso: bool(
        caso.expect.get("scientific_format") or caso.expect.get("required_sections")
    ),
))
