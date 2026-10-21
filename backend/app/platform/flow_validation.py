"""Validación del grafo que dibuja el Flow Designer (BUG-001 / VAL-004).

Las aristas del lienzo son datos que llegan del cliente, así que la validación del
navegador es una ayuda y no una garantía: cualquiera puede hacer `PUT /flows`
saltándose la interfaz. Este módulo es la validación que manda; el frontend
(`platform/flowValidation.js`) aplica el mismo contrato para dar feedback al
arrastrar.

Cada problema es un `FlowIssue` estructurado —código de regla, nodos y aristas
implicados— para que la interfaz pueda resaltar exactamente lo que falla en lugar
de enseñar un texto suelto.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Tuple

ERROR = "error"
WARNING = "warning"

SELF_LOOP = "self_loop"


@dataclass(frozen=True)
class FlowIssue:
    code: str
    severity: str
    message: str
    nodes: Tuple[str, ...] = ()
    edges: Tuple[str, ...] = ()

    def as_dict(self) -> Dict[str, Any]:
        datos = asdict(self)
        datos["nodes"] = list(self.nodes)
        datos["edges"] = list(self.edges)
        return datos


def _edge_id(edge: Dict[str, Any]) -> str:
    return str(edge.get("id") or f"{edge.get('source')}->{edge.get('target')}")


def _edges(edges: Iterable[Any]) -> List[Dict[str, Any]]:
    return [e for e in edges or [] if isinstance(e, dict)]


def self_loops(edges: Iterable[Any]) -> List[FlowIssue]:
    """Aristas que unen un nodo consigo mismo."""
    return [
        FlowIssue(
            code=SELF_LOOP,
            severity=ERROR,
            message="Un agente no puede conectarse consigo mismo",
            nodes=(str(e["source"]),),
            edges=(_edge_id(e),),
        )
        for e in _edges(edges)
        if e.get("source") is not None and e.get("source") == e.get("target")
    ]


def validate_flow(nodes: Iterable[Any], edges: Iterable[Any]) -> List[FlowIssue]:
    """Todos los problemas del grafo, bloqueantes y avisos."""
    return self_loops(edges)


def blocking(issues: Iterable[FlowIssue]) -> List[FlowIssue]:
    return [i for i in issues if i.severity == ERROR]
