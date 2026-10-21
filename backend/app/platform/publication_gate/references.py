"""Estructura de las referencias (SPEC-032 AC2, FW V09 nivel 1).

Determinista y sin LLM. Se evalúa *después* de resolver y enriquecer las fuentes
(AC3): una fuente cuyo DOI se resolvió ya trae autores, año y publicación.
"""
from typing import Any, Iterable

from app.platform.publication_gate.types import CriterionResult, CriterionStatus

CRITERION = "reference_structure"

_EMPTY_VALUES = {"", "n/a", "none", "null", "na"}

# Campo lógico → claves de la fuente que lo pueden aportar.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "identifier": ("doi", "url"),
    "authors": ("authors",),
    "year": ("year",),
    "journal": ("journal",),
}


def _val(source: dict, key: str) -> str:
    v = str(source.get(key, "") or "").strip()
    return "" if v.lower() in _EMPTY_VALUES else v


def _has_identifier(source: dict) -> bool:
    if _val(source, "doi"):
        return True
    # Las pseudo-URL internas (local://, synthesis://) no identifican nada.
    return _val(source, "url").lower().startswith(("http://", "https://"))


def missing_fields(source: dict) -> list[str]:
    """Campos obligatorios que la fuente no trae, en orden estable."""
    missing = []
    for name, keys in REQUIRED_FIELDS.items():
        present = _has_identifier(source) if name == "identifier" else any(
            _val(source, k) for k in keys
        )
        if not present:
            missing.append(name)
    return missing


def is_citable(source: dict) -> bool:
    """La síntesis paramétrica del LLM no es una fuente: no se evalúa ni se imprime."""
    return not str(source.get("url", "") or "").startswith("synthesis://")


def check_reference_structure(sources: Iterable[dict[str, Any]]) -> CriterionResult:
    evidence = []
    for index, source in enumerate((s for s in sources or [] if is_citable(s)), start=1):
        missing = missing_fields(source)
        if missing:
            evidence.append(
                {
                    "index": index,
                    "title": _val(source, "title") or _val(source, "filename") or "(sin título)",
                    "missing": missing,
                }
            )
    status = CriterionStatus.FAILED if evidence else CriterionStatus.PASSED
    return CriterionResult(CRITERION, status, evidence)
