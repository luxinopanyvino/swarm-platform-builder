"""Una sola puerta a `published` (SPEC-032 AC10 y AC13, ADR-0011).

`can_publish` decide si un artículo puede publicarse, y `assign_published` es el
**único** sitio del código que asigna `ArticleStatus.PUBLISHED`: no la asigna sin
una decisión que lo permita. Un test recorre el código fuente y falla si aparece
otra asignación, de modo que "hay una sola puerta" es verificable y no una
intención de diseño.

La regla (FW §3, §10): publicar exige las tres cosas a la vez —

1. una **revisión que aprueba** (≥ 80 y sin bloqueante de juicio),
2. una **compuerta sin bloqueantes** sobre el texto actual,
3. una **aprobación humana explícita** de ese mismo texto.

Con `enforce=False` (`PUBLICATION_GATE_ENFORCE`, AC16) las dos primeras se
registran como avisos y no impiden publicar; la aprobación humana sigue siendo
obligatoria en ambos modos.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, Optional

from app.platform.publication_gate.review import judgment_blockers


@dataclass(frozen=True)
class GateState:
    """Estado de la compuerta para el texto actual del artículo."""

    passed: bool
    #: el informe describe el texto que hay ahora (la huella coincide)
    current: bool


@dataclass(frozen=True)
class Approval:
    """Aprobación humana explícita."""

    user_id: Any
    #: la huella aprobada coincide con el texto actual
    current: bool = True


@dataclass(frozen=True)
class PublishDecision:
    allowed: bool
    #: motivos por los que no se puede publicar, vacío si se puede
    reasons: tuple = ()
    #: problemas que no impiden publicar porque `enforce` está apagado
    warnings: tuple = ()
    #: de dónde viene el permiso: `approval`, `legacy_no_gate` o `dev_seed`
    basis: str = "approval"
    detail: dict = field(default_factory=dict)


def can_publish(
    *,
    review: Optional[Mapping[str, Any]],
    gate: Optional[GateState],
    approval: Optional[Approval],
    enforce: bool = True,
) -> PublishDecision:
    reasons: list = []
    warnings: list = []

    # 1. Revisión. Sin revisión interpretable —o sin revisión— no aprueba.
    if review is None:
        review_problems = ["review_missing"]
    else:
        review_problems = judgment_blockers(review)

    # 2. Compuerta sobre el texto actual.
    if gate is None:
        gate_problems = ["no_gate_report"]
    elif not gate.current:
        gate_problems = ["gate_stale"]
    elif not gate.passed:
        gate_problems = ["gate_blockers"]
    else:
        gate_problems = []

    # Estas dos se relajan con el modo aviso; la 3.ª, nunca.
    (reasons if enforce else warnings).extend(review_problems + gate_problems)

    # 3. Aprobación humana de este texto.
    if approval is None:
        reasons.append("no_approval")
    elif not approval.current:
        reasons.append("approval_stale")

    return PublishDecision(
        allowed=not reasons, reasons=tuple(reasons), warnings=tuple(warnings), basis="approval",
        detail={"review_problems": review_problems, "gate_problems": gate_problems},
    )


def legacy_decision() -> PublishDecision:
    """Un proyecto que no declara `gate:` conserva el comportamiento anterior."""
    return PublishDecision(allowed=True, basis="legacy_no_gate")


def dev_seed_decision() -> PublishDecision:
    """La siembra de demostración crea contenido ya publicado. Solo con la siembra
    de desarrollo encendida, que `_DEV_ONLY_FLAGS` apaga con `DEBUG=false`."""
    from app.core.config import settings

    if not settings.ENABLE_DEV_SEED:
        raise PermissionError("La siembra de desarrollo no está habilitada")
    return PublishDecision(allowed=True, basis="dev_seed")


def assign_published(article: Any, decision: PublishDecision, *, now: Optional[datetime] = None) -> None:
    """Marca el artículo como publicado. **Único** punto que asigna `PUBLISHED`."""
    from app.models.enums import ArticleStatus

    if not decision.allowed:
        raise PermissionError(
            "No se puede publicar: " + (", ".join(decision.reasons) or "decisión no permitida")
        )
    article.status = ArticleStatus.PUBLISHED
    article.published_at = now or datetime.utcnow()
