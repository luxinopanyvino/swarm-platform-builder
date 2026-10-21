"""Completitud de las referencias impresas (SPEC-032 / T20.15 / AC2).

Antes de SPEC-032 el Formateador imprimía una fuente con el campo vacío **omitido en
silencio**: el texto parecía correcto y la referencia era un nombre de archivo. La
regla ahora es que una referencia que se imprime lleva **año e identificador
resoluble** (DOI o enlace); las incompletas no se imprimen y se informan.

Es una comprobación determinista sobre el texto, sin opinar: lee la sección de
referencias y exige a cada entrada un año y un identificador. Es la parte
observable desde la salida de la regla de la compuerta (que opera sobre las
fuentes estructuradas); no la sustituye.
"""
from __future__ import annotations

import re

from evals.agent_behavior.metrics import Metric, register, skipped
from evals.agent_behavior.models import CaseResult, EvalCase, MetricResult

NOMBRE = "reference_completeness"

_ENCABEZADO = re.compile(
    r"^#{1,6}[ \t]*(referencias|references|bibliograf[ií]a|bibliography)[ \t:]*$",
    re.IGNORECASE | re.MULTILINE,
)
_ANIO = re.compile(r"\b(19|20)\d{2}[a-z]?\b")
_IDENTIFICADOR = re.compile(r"https?://\S+|\bdoi:\s*\S+", re.IGNORECASE)


def referencias(texto: str) -> list[str]:
    """Entradas de la sección de referencias, una por línea no vacía."""
    encabezados = list(_ENCABEZADO.finditer(texto or ""))
    if not encabezados:
        return []
    cola = texto[encabezados[-1].end():]
    return [linea.strip() for linea in cola.splitlines() if linea.strip()]


def _evaluar(caso: EvalCase, resultado: CaseResult) -> MetricResult:
    entradas = referencias(resultado.output or "")
    if not entradas:
        return MetricResult(
            name=NOMBRE, score=0.0, passed=False,
            detail="no hay sección de referencias que evaluar: un caso que exige referencias completas las necesita",
        )
    incompletas = []
    for entrada in entradas:
        faltan = []
        if not _ANIO.search(entrada):
            faltan.append("año")
        if not _IDENTIFICADOR.search(entrada):
            faltan.append("identificador")
        if faltan:
            incompletas.append(f"«{entrada[:60]}» sin {' ni '.join(faltan)}")
    puntuacion = 100.0 * (len(entradas) - len(incompletas)) / len(entradas)
    return MetricResult(
        name=NOMBRE, score=round(puntuacion, 2), passed=not incompletas,
        detail="todas las referencias llevan año e identificador" if not incompletas
        else "; ".join(incompletas),
    )


register(Metric(
    name=NOMBRE,
    description="Porcentaje de referencias impresas que llevan año e identificador resoluble.",
    run=_evaluar,
    applies_to=lambda caso: bool((caso.expect or {}).get("complete_references")),
))
