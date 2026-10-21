"""La compuerta: ejecuta los criterios en orden y compone el informe (SPEC-032 AC5).

Se evalúa sobre el **texto final** (el que se publicaría) y no nombra agentes ni
disciplinas: lo que se aplica y con qué parámetros lo declara el proyecto.
Orden (FW §20, los criterios sin LLM primero): 1) resolver y enriquecer las
referencias, 2) validar su estructura, 3) marcadores, 4) estructura IMRaD,
5) criterios `not_implemented`.
"""
from dataclasses import dataclass, field
from typing import Any

from app.platform.publication_gate.config import GateConfig
from app.platform.publication_gate.placeholders import check_placeholders
from app.platform.publication_gate.reference_resolver import check_reference_existence
from app.platform.publication_gate.references import check_reference_structure
from app.platform.publication_gate.structure import check_structure
from app.platform.publication_gate.types import CriterionResult


@dataclass
class GateReport:
    criteria: list
    #: Fuentes tras resolver y enriquecer; las que usa el resto de la compuerta.
    sources: list = field(default_factory=list)
    #: Criterios declarados sin dato todavía: `{"id", "phase"}`. No bloquean.
    pending: list = field(default_factory=list)

    @property
    def blockers(self) -> list:
        return [c for c in self.criteria if c.blocking]

    @property
    def passed(self) -> bool:
        return not self.blockers

    def as_dict(self) -> dict:
        return {
            "passed": self.passed,
            "criteria": [
                {"criterion": c.criterion, "status": c.status.value, "evidence": c.evidence}
                for c in self.criteria
            ],
            "pending": self.pending,
        }


async def evaluate_gate(
    text: str, sources: list, config: GateConfig, **resolver_kwargs: Any
) -> GateReport:
    existence, enriched = await check_reference_existence(
        sources, config.references, **resolver_kwargs
    )
    criteria: list[CriterionResult] = [
        existence,
        check_reference_structure(enriched),
        check_placeholders(text, config.placeholders),
        check_structure(text, config.sections, config.titles),
    ]
    pending = [{"id": p.id, "phase": p.phase} for p in config.pending]
    return GateReport(criteria=criteria, sources=enriched, pending=pending)
