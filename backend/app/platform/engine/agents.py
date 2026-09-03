"""Registro de agentes del motor (SPEC-013 / T8.3 / AC5+AC8).

`Orchestrator.compile_graph` tenía los cinco agentes de AlejandrIA escritos en un
`dict` dentro del motor. Mientras solo haya un proyecto, se nota poco; en una
plataforma donde cada proyecto trae los suyos, ese `dict` es el sitio que hay que
editar para dar de alta un agente — o sea, no hay alta de agentes.

Aquí un agente es un **dato**: su nombre, las capacidades que compone y de dónde
sale su implementación. El motor resuelve nombres contra este registro y no
conoce a ninguno en concreto. T8.4 dará de alta los agentes de un proyecto desde
su `template.yaml`; de momento los registra el propio proyecto en Python.

Declarar `requires` no es burocracia: es lo que permite decirle a alguien que su
proyecto **no puede** ejecutar este agente porque no provee `rag`, antes de
arrancar el pipeline y no a mitad del tercer paso.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.platform.capabilities.binding import CapabilityBundle, bind

logger = logging.getLogger(__name__)

#: Modos del flag `AGENT_ENGINE` (SPEC-013 / AC8).
MODO_ADAPTERS = "adapters"
MODO_CAPACIDADES = "capabilities"


class UnknownAgent(ValueError):
    """Nadie sabe ejecutar un agente con ese nombre."""


@dataclass(frozen=True)
class AgentSpec:
    """Un agente del motor, descrito como dato.

    Attributes:
        name: nombre con el que aparece en `flow_sequence`.
        entrypoint: referencia perezosa ``"paquete.modulo:funcion"`` a su runner.
        requires: **nombres** de las capacidades que compone. Con el flag en
            `capabilities` se resuelven desde el registro y se le inyectan; con
            el flag en `adapters` el runner usa sus imports de siempre. Por
            nombre y no por tipo porque un tipo puede tener varias: el RAG
            expone una búsqueda que devuelve texto y otra que devuelve
            resultados con metadatos.
        description: para la interfaz y los errores.
    """

    name: str
    entrypoint: str
    requires: Tuple[str, ...] = field(default_factory=tuple)
    description: str = ""

    def resolve(self) -> Callable:
        modulo, _, atributo = self.entrypoint.partition(":")
        return getattr(import_module(modulo), atributo)


_REGISTRO: Dict[str, AgentSpec] = {}


def register_agent(spec: AgentSpec) -> AgentSpec:
    _REGISTRO[spec.name] = spec
    return spec


def get_agent(name: str) -> Optional[AgentSpec]:
    return _REGISTRO.get(name)


def list_agents() -> List[AgentSpec]:
    return list(_REGISTRO.values())


def bundle_for(name: str) -> Optional[CapabilityBundle]:
    """Capacidades resueltas del agente, o `None` si no declara ninguna."""
    spec = get_agent(name)
    if spec is None or not spec.requires:
        return None
    return bind(spec.requires)


def resolve_runner(
    name: str,
    fallback_loader: Callable[[str], Optional[Callable]] | None = None,
) -> Callable:
    """Función ejecutable del agente `name`.

    Busca primero en el registro; si no está, delega en `fallback_loader` (los
    agentes dinámicos de `.agent.md`, que no se declaran en código). Si tampoco,
    falla con un mensaje que dice qué agentes **sí** existen: un flujo con un
    nombre mal escrito es el error más fácil de cometer al componer un pipeline.
    """
    spec = get_agent(name)
    if spec is not None:
        return spec.resolve()

    if fallback_loader is not None:
        runner = fallback_loader(name)
        if runner is not None:
            return runner

    conocidos = ", ".join(sorted(_REGISTRO)) or "(ninguno)"
    raise UnknownAgent(
        f"Agente desconocido '{name}': no está registrado en el motor ni tiene "
        f"perfil .agent.md. Registrados: {conocidos}"
    )
