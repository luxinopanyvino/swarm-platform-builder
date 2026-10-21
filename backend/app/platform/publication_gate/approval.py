"""Reglas de la aprobación humana explícita (SPEC-032 AC8, ADR-0011).

Una sola función decide si una persona puede aprobar un artículo, para que
`approve` y, en T20.11, `publish` apliquen exactamente las mismas reglas. Es pura:
recibe lo que necesita y devuelve el motivo de la denegación, si lo hay; el
router lo traduce a HTTP.

Dos familias de denegación, a propósito en este orden:

* **403 — quién.** Solo el revisor asignado o un administrador, y nunca el
  propietario del artículo (quien lanzó el pipeline): nadie se aprueba a sí mismo.
  La excepción es un entorno de un solo usuario, y solo con `DEBUG` encendido.
* **409 — qué.** El artículo debe tener autor responsable declarado (FW V13) y un
  informe de compuerta vigente, de este texto y sin bloqueantes. Con
  `PUBLICATION_GATE_ENFORCE=false` estas comprobaciones se registran pero no
  bloquean (AC16): la aprobación humana sigue siendo obligatoria.
"""
from dataclasses import dataclass
from typing import Any, Optional

from app.platform.publication_gate.service import is_current


@dataclass(frozen=True)
class Denial:
    status: int
    code: str
    message: str


def gate_problem(article: Any, report: Any) -> Optional[Denial]:
    """Por qué el estado de la compuerta impide aprobar, o `None` si no lo impide."""
    if getattr(article, "responsible_author_id", None) is None:
        return Denial(409, "no_responsible_author",
                      "El artículo no tiene autor responsable declarado")
    if report is None:
        return Denial(409, "no_gate_report",
                      "El artículo no tiene informe de compuerta: hay que evaluarlo antes de aprobar")
    if not is_current(report, article):
        return Denial(409, "text_changed",
                      "El texto cambió desde la última evaluación de la compuerta: hay que reevaluarlo")
    if not (report.criteria or {}).get("passed", False):
        return Denial(409, "gate_blockers",
                      "El último informe de la compuerta tiene bloqueantes")
    return None


def approval_denial(
    *,
    article: Any,
    user_id: Any,
    role: str,
    report: Any,
    enforce: bool,
    allow_self_approval: bool,
) -> tuple[Optional[Denial], Optional[Denial]]:
    """`(denegación, aviso)`.

    La denegación impide aprobar. El aviso es un problema de compuerta que no
    bloquea porque `enforce` está apagado; el llamador lo deja en el registro.
    """
    is_admin = role == "admin"
    is_assigned = getattr(article, "reviewer_id", None) == user_id
    if not (is_admin or is_assigned):
        return Denial(403, "not_reviewer",
                      "Solo el administrador o el revisor asignado puede aprobar artículos"), None
    if article.author_id == user_id and not allow_self_approval:
        return Denial(403, "owner_cannot_approve",
                      "Quien lanzó el pipeline no puede aprobar su propio artículo"), None

    problem = gate_problem(article, report)
    if problem is None:
        return None, None
    return (problem, None) if enforce else (None, problem)
