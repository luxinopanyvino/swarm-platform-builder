"""Compuerta de publicación determinista (SPEC-032, ADR-0011).

Genérica: no nombra agentes ni disciplinas. Cada criterio es una función pura
sobre el texto final y devuelve un `CriterionResult`.
"""
from app.platform.publication_gate.types import (
    BLOCKING_STATUSES,
    CriterionResult,
    CriterionStatus,
)

__all__ = ["BLOCKING_STATUSES", "CriterionResult", "CriterionStatus"]
