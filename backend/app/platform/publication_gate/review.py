"""Resultado de la revisión como insumo de la decisión de publicar (SPEC-032 AC10, AC15).

Definición provisional de **bloqueante de juicio** de la Fase 1, hasta que la
Fase 3 dé salida por criterio: la revisión no aprueba si `approval_score < 80`,
si `coherent` es falso o si `review_status` es `not_verified` (el Revisor no pudo
producir una revisión interpretable).
"""
from typing import Any, Mapping

REVIEW_OK = "ok"
REVIEW_NOT_VERIFIED = "not_verified"
#: No hubo revisión (el flujo no incluía al Revisor): tampoco aprueba.
REVIEW_NOT_RUN = "not_run"

#: El mismo umbral que aplica el enrutador de revisión (`projects/*/template.yaml`).
APPROVAL_THRESHOLD = 80


def judgment_blockers(review: Mapping[str, Any]) -> list[str]:
    """Motivos por los que la revisión no aprueba; vacío si aprueba."""
    status = review.get("review_status", REVIEW_OK)
    if status == REVIEW_NOT_RUN:
        return ["review_missing"]
    if status != REVIEW_OK:
        # Sin revisión interpretable no hay puntuación que mirar.
        return ["review_not_verified"]
    blockers = []
    score = review.get("approval_score")
    if not isinstance(score, (int, float)) or score < APPROVAL_THRESHOLD:
        blockers.append("score_below_threshold")
    if review.get("coherent") is False:
        blockers.append("not_coherent")
    return blockers


def review_approves(review: Mapping[str, Any]) -> bool:
    return not judgment_blockers(review)
