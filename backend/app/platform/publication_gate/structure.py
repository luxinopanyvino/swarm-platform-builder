"""Estructura del manuscrito (SPEC-032 AC11, FW V03).

IMRaD por defecto: Introducción, Métodos, Resultados, Discusión y Referencias, en
ese orden y cada una en su sección. Los títulos aceptados salen de un diccionario
por idioma que declara el proyecto (`gate.structure`): el Redactor genera
«Metodología», y otro proyecto puede exigir otra estructura sin tocar este módulo.
"""
import re
import unicodedata
from typing import Mapping, Optional, Sequence

from app.platform.publication_gate.types import CriterionResult, CriterionStatus

CRITERION = "imrad_structure"

_HEADING = re.compile(r"(?m)^[ \t]*#{1,6}[ \t]+(.+?)[ \t#]*$")


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"^[\d.\s)\-]+", "", t)  # «3. Resultados» → «resultados»
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def _check_language(
    headings: list[tuple[int, str]], sections: Sequence[str], titles: Mapping[str, Sequence[str]]
) -> list[dict]:
    accepted = {s: {_norm(t) for t in titles.get(s, ())} for s in sections}
    first: dict[str, int] = {}
    issues: list[dict] = []
    fused: set[str] = set()
    for index, heading in headings:
        for section in sections:
            if heading in accepted[section]:
                first.setdefault(section, index)
        # Un solo encabezado que nombra dos secciones («Resultados y Discusión»).
        partes = re.split(r"\s+(?:y|and)\s+", heading)
        if len(partes) > 1:
            hit = [s for s in sections if any(p.strip() in accepted[s] for p in partes)]
            if len(hit) > 1:
                issues.append({"section": " + ".join(hit), "problem": "fused"})
                fused.update(hit)
    for section in sections:
        if section not in first and section not in fused:
            issues.append({"section": section, "problem": "missing"})
    presentes = [s for s in sections if s in first]
    for previa, actual in zip(presentes, presentes[1:]):
        if first[actual] < first[previa]:
            issues.append({"section": actual, "problem": "out_of_order", "before": previa})
    return issues


def check_structure(
    text: str, sections: Sequence[str], titles_by_language: Mapping[str, Mapping[str, Sequence[str]]]
) -> CriterionResult:
    """Pasa si el texto cumple la estructura en **alguno** de los idiomas declarados;
    si no, informa del idioma con menos incumplimientos."""
    headings = [(m.start(), _norm(m.group(1))) for m in _HEADING.finditer(text or "")]
    mejor: Optional[tuple[str, list[dict]]] = None
    for language, titles in titles_by_language.items():
        issues = _check_language(headings, sections, titles)
        if not issues:
            return CriterionResult(CRITERION, CriterionStatus.PASSED, [])
        if mejor is None or len(issues) < len(mejor[1]):
            mejor = (language, issues)
    if mejor is None:
        # Sin diccionario no se puede comprobar: lo que no se comprueba no se aprueba.
        return CriterionResult(
            CRITERION, CriterionStatus.NOT_VERIFIED, [{"problem": "no_structure_declared"}]
        )
    return CriterionResult(
        CRITERION, CriterionStatus.FAILED, [{**i, "language": mejor[0]} for i in mejor[1]]
    )
