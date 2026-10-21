"""Detector de marcadores de posición en el texto final (SPEC-032 AC1, FW V01).

Determinista y sin LLM. Se ignora el código delimitado (``` ```) y en línea
(`` ` ``): un manuscrito que *habla de* un marcador puede citarlo entre comillas
de código.
"""
import re

from app.platform.publication_gate.types import CriterionResult, CriterionStatus

CRITERION = "placeholders"

# Lista cerrada de AC1. Se amplía en `template.yaml` (`gate.placeholders`).
DEFAULT_PLACEHOLDERS: tuple[str, ...] = (
    "(Author, Year)",
    "(Autor, Año)",
    "(Author et al., Year)",
    "[?]",
    "[??]",
    "[citation needed]",
    "[cita necesaria]",
    "TODO",
    "TBD",
    "XXX",
)

_FENCE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_INLINE = re.compile(r"`[^`\n]*`")


def _blank_code(text: str) -> str:
    """Sustituye el código por espacios, conservando longitudes y saltos de línea,
    para que las posiciones sigan siendo las del texto original."""

    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))

    return _INLINE.sub(blank, _FENCE.sub(blank, text))


def _pattern(marker: str) -> re.Pattern:
    escaped = re.escape(marker)
    if marker[0].isalnum():
        # Las palabras (TODO, TBD, XXX) cuentan enteras y en mayúsculas: «todo el
        # mundo» es español corriente, no un marcador.
        return re.compile(rf"(?<!\w){escaped}(?!\w)")
    return re.compile(escaped, re.IGNORECASE)


def check_placeholders(
    text: str, markers: tuple[str, ...] | list[str] = DEFAULT_PLACEHOLDERS
) -> CriterionResult:
    visible = _blank_code(text or "")
    evidence: list[dict] = []
    for marker in markers:
        for m in _pattern(marker).finditer(visible):
            line = visible.count("\n", 0, m.start()) + 1
            col = m.start() - (visible.rfind("\n", 0, m.start()) + 1) + 1
            evidence.append(
                {"pattern": marker, "offset": m.start(), "line": line, "column": col}
            )
    evidence.sort(key=lambda e: e["offset"])
    status = CriterionStatus.FAILED if evidence else CriterionStatus.PASSED
    return CriterionResult(CRITERION, status, evidence)
