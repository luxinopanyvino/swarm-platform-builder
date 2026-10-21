"""Validación del grafo que dibuja el Flow Designer (BUG-001 / VAL-004).

Las aristas del lienzo son datos que llegan del cliente, así que la validación del
navegador es una ayuda y no una garantía: cualquiera puede hacer `PUT /flows`
saltándose la interfaz. Este módulo es la validación que manda; el frontend
(`platform/flowValidation.js`) aplica el mismo contrato para dar feedback al
arrastrar, con las reglas que sirve `GET /api/v1/flows/rules`.

Cada problema es un `FlowIssue` estructurado —código de regla, nodos y aristas
implicados— para que la interfaz pueda resaltar exactamente lo que falla en lugar
de enseñar un texto suelto.

Las reglas de dependencia entre agentes son **datos** (`FlowRules`), declaradas
por cada proyecto en `graph.flow_rules` de su `template.yaml`; este módulo no
nombra a ningún agente concreto.

**Qué significa «antes».** El motor ejecuta `flow_sequence`, no las aristas. Así
que el orden de ejecución es el topológico de las aristas y, donde no hay arista
que lo decida, el orden en que se soltaron los agentes en el lienzo.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ERROR = "error"
WARNING = "warning"

SELF_LOOP = "self_loop"
CYCLE = "cycle"
ORPHAN = "orphan"
MISSING_DEPENDENCY = "missing_dependency"
WRONG_ORDER = "wrong_order"


# ── Reglas (datos, no código) ───────────────────────────────────────────────

@dataclass(frozen=True)
class Requirement:
    """`agent` necesita que corra antes algún agente de `any_of`.

    `satisfied_by_existing_output` marca las dependencias que ya cumple el
    resultado de una ejecución anterior: re-publicar un artículo ya redactado no
    necesita al redactor en el flujo.
    """

    agent: str
    any_of: Tuple[str, ...]
    severity: str = ERROR
    satisfied_by_existing_output: bool = False


@dataclass(frozen=True)
class FlowRules:
    """Reglas de un proyecto. Las declara `graph.flow_rules` de su `template.yaml`."""

    requires: Tuple[Requirement, ...] = field(default_factory=tuple)
    #: severidad de un agente sin ninguna conexión en un flujo de varios; `None` lo desactiva.
    orphans: Optional[str] = WARNING

    def as_dict(self) -> Dict[str, Any]:
        return {
            "orphans": self.orphans,
            "requires": [
                {
                    "agent": r.agent,
                    "any_of": list(r.any_of),
                    "severity": r.severity,
                    "satisfied_by_existing_output": r.satisfied_by_existing_output,
                }
                for r in self.requires
            ],
        }


NO_RULES = FlowRules(requires=(), orphans=None)


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


# ── Lectura tolerante del grafo ─────────────────────────────────────────────

def _edge_id(edge: Dict[str, Any]) -> str:
    return str(edge.get("id") or f"{edge.get('source')}->{edge.get('target')}")


def _edges(edges: Iterable[Any]) -> List[Dict[str, Any]]:
    return [e for e in edges or [] if isinstance(e, dict)]


def _agent_id(node: Dict[str, Any]) -> Optional[str]:
    data = node.get("data")
    agent = data.get("agentId") if isinstance(data, dict) else None
    return str(agent) if agent else None


def _label(agent: str) -> str:
    return agent[:1].upper() + agent[1:]


def _agent_nodes(nodes: Iterable[Any]) -> List[Tuple[str, str]]:
    """`(id_de_nodo, agente)` en el orden del lienzo, solo para nodos de agente."""
    salida = []
    for nodo in nodes or []:
        if isinstance(nodo, dict) and nodo.get("id") is not None and _agent_id(nodo):
            salida.append((str(nodo["id"]), _agent_id(nodo)))
    return salida


def _links(edges: Iterable[Any], known: set) -> List[Tuple[str, str, str]]:
    """`(arista, origen, destino)` entre nodos conocidos, sin autoconexiones."""
    return [
        (_edge_id(e), str(e["source"]), str(e["target"]))
        for e in _edges(edges)
        if e.get("source") is not None
        and e.get("target") is not None
        and e["source"] != e["target"]
        and str(e["source"]) in known
        and str(e["target"]) in known
    ]


# ── Reglas estructurales ────────────────────────────────────────────────────

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


def _cycle_nodes(order: List[str], links: List[Tuple[str, str, str]]) -> set:
    """Nodos que están en algún ciclo (no los que solo cuelgan de uno)."""
    vivos = set(order)
    cambio = True
    while cambio:
        cambio = False
        for n in list(vivos):
            entra = any(t == n and s in vivos for _, s, t in links)
            sale = any(s == n and t in vivos for _, s, t in links)
            if not (entra and sale):
                vivos.discard(n)
                cambio = True
    return vivos


def effective_order(nodes: Iterable[Any], edges: Iterable[Any]) -> List[str]:
    """Orden de ejecución de los nodos: topológico, y por orden del lienzo en los empates.

    Un ciclo no tiene orden; sus nodos se añaden al final en el orden del lienzo.
    """
    agentes = _agent_nodes(nodes)
    indice = {n: i for i, (n, _) in enumerate(agentes)}
    links = _links(edges, set(indice))
    entrantes = {n: 0 for n in indice}
    for _, _, t in links:
        entrantes[t] += 1
    listos = sorted((n for n, c in entrantes.items() if c == 0), key=indice.get)
    orden: List[str] = []
    while listos:
        n = listos.pop(0)
        orden.append(n)
        for _, s, t in links:
            if s == n:
                entrantes[t] -= 1
                if entrantes[t] == 0:
                    listos.append(t)
        listos.sort(key=indice.get)
    orden += sorted((n for n in indice if n not in orden), key=indice.get)
    return orden


# ── Reglas de dependencia ───────────────────────────────────────────────────

def _check_requirements(
    agents_in_order: Sequence[Tuple[str, str]],
    rules: FlowRules,
    edges: List[Tuple[str, str, str]],
    existing_output: bool,
) -> List[FlowIssue]:
    """`agents_in_order`: `(id_de_nodo, agente)` en orden de ejecución."""
    issues: List[FlowIssue] = []
    for req in rules.requires:
        if existing_output and req.satisfied_by_existing_output:
            continue
        for pos, (nodo, agente) in enumerate(agents_in_order):
            if agente != req.agent:
                continue
            antes = {a for _, a in agents_in_order[:pos]}
            if antes & set(req.any_of):
                continue
            despues = [n for n, a in agents_in_order[pos + 1:] if a in req.any_of]
            requeridos = ", ".join(_label(a) for a in req.any_of)
            if despues:
                codigo = WRONG_ORDER
                mensaje = f"{_label(agente)} no puede ejecutarse antes de {requeridos}"
                implicadas = tuple(e for e, s, t in edges if s == nodo and t in despues)
            else:
                codigo = MISSING_DEPENDENCY
                mensaje = f"{_label(agente)} necesita {requeridos} antes en el flujo"
                implicadas = tuple(e for e, _, t in edges if t == nodo)
            issues.append(FlowIssue(
                code=codigo,
                severity=req.severity,
                message=mensaje,
                nodes=(nodo, *despues),
                edges=implicadas,
            ))
    return issues


def validate_flow(
    nodes: Iterable[Any],
    edges: Iterable[Any],
    rules: FlowRules = NO_RULES,
    flow_sequence: Optional[Sequence[str]] = None,
    existing_output: bool = False,
) -> List[FlowIssue]:
    """Todos los problemas del grafo, bloqueantes y avisos.

    Si llega `flow_sequence` (lo que se va a ejecutar de verdad), el orden se
    comprueba contra ella; si no, contra el orden derivado de las aristas.
    """
    issues = self_loops(edges)
    agentes = _agent_nodes(nodes)
    links = _links(edges, {n for n, _ in agentes})

    ciclo = _cycle_nodes([n for n, _ in agentes], links)
    if ciclo:
        nombres = ", ".join(_label(a) for n, a in agentes if n in ciclo)
        issues.append(FlowIssue(
            code=CYCLE,
            severity=ERROR,
            message=f"El flujo tiene un ciclo entre {nombres}",
            nodes=tuple(n for n, _ in agentes if n in ciclo),
            edges=tuple(e for e, s, t in links if s in ciclo and t in ciclo),
        ))

    if rules.orphans and len(agentes) > 1:
        conectados = {x for _, s, t in links for x in (s, t)}
        for nodo, agente in agentes:
            if nodo not in conectados:
                issues.append(FlowIssue(
                    code=ORPHAN,
                    severity=rules.orphans,
                    message=f"{_label(agente)} no está conectado al flujo",
                    nodes=(nodo,),
                ))

    if flow_sequence is not None:
        # Sin nodos que señalar, las aristas no se pueden atribuir.
        issues += validate_sequence(flow_sequence, rules, existing_output)
    else:
        por_id = dict(agentes)
        orden = [(n, por_id[n]) for n in effective_order(nodes, edges)]
        issues += _check_requirements(orden, rules, links, existing_output)
    return issues


def validate_sequence(
    flow_sequence: Sequence[str], rules: FlowRules, existing_output: bool = False
) -> List[FlowIssue]:
    """Comprueba solo el orden de una secuencia (el camino de `POST /agents/{id}/run`)."""
    return _check_requirements(
        [(f"#{i}", a) for i, a in enumerate(flow_sequence)], rules, [], existing_output
    )


DEPENDENCY_CODES = (MISSING_DEPENDENCY, WRONG_ORDER)


def relax_dependencies(issues: Iterable[FlowIssue]) -> List[FlowIssue]:
    """Degrada a aviso las reglas de dependencia (modo `FLOW_RULES_ENFORCE=false`).

    Los ciclos y las autoconexiones no se degradan: no tienen un modo
    «ya veremos», rompen la ejecución.
    """
    return [
        FlowIssue(i.code, WARNING, i.message, i.nodes, i.edges)
        if i.code in DEPENDENCY_CODES and i.severity == ERROR else i
        for i in issues
    ]


def blocking(issues: Iterable[FlowIssue]) -> List[FlowIssue]:
    return [i for i in issues if i.severity == ERROR]
