"""Resolución de capacidades para un agente (SPEC-013 / T8.3 / AC8).

Los adapters importan hoy su infraestructura directamente
(`from app.platform.capabilities.rag import semantic_search_results`). Eso ata
cada agente a **una** implementación concreta: un proyecto no puede traer su
propio proveedor de RAG o de LLM sin editar el código del agente, que es
justamente lo que una plataforma no-code tiene que permitir.

Un `CapabilityBundle` es el conjunto de capacidades que un agente compone,
resuelto desde el registro. Se inyecta en el estado (como ya se inyectan `_log` y
`_emit_token`) y el agente lo consulta en vez de importar. Cuando no hay bundle
—el camino heredado—, el agente usa sus imports de siempre: por eso los dos
caminos dan el mismo resultado y se pueden conmutar con el flag sin borrar nada
(la mitigación que pide la tabla de riesgos de SPEC-013).

Se resuelve por **nombre** y no por tipo. Un tipo puede tener varias capacidades
—el RAG expone una búsqueda que devuelve texto y otra que devuelve resultados con
metadatos, y los agentes usan una u otra— así que pedir «una capacidad de tipo
rag» no basta para saber cuál quieres.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, Optional

from app.platform.capabilities.registry import CapabilityNotAvailable, get

#: Clave con la que el bundle viaja en el estado del grafo. Con guion bajo
#: delante, igual que `_log`, para que se distinga de los datos del artículo.
CLAVE_ESTADO = "_capabilities"


class MissingCapability(LookupError):
    """El proyecto no provee una capacidad que el agente declara necesitar."""


@dataclass(frozen=True)
class CapabilityBundle:
    """Capacidades resueltas, por nombre.

    Se resuelven **una vez por paso** y no en cada llamada: importar es barato
    pero no gratis, y sobre todo así un agente no puede acabar usando dos
    implementaciones distintas de la misma capacidad en la misma pasada.
    """

    proveedores: Mapping[str, Any]

    def get(self, nombre: str) -> Any:
        try:
            return self.proveedores[nombre]
        except KeyError as error:
            raise MissingCapability(
                f"La capacidad '{nombre}' no está disponible en esta ejecución"
            ) from error

    def has(self, nombre: str) -> bool:
        return nombre in self.proveedores


def bind(nombres: Iterable[str]) -> CapabilityBundle:
    """Resuelve las capacidades pedidas desde el registro.

    Falla **al construir el bundle** y no al usarlo: un proyecto al que le falta
    una capacidad debe enterarse antes de arrancar el pipeline, no a mitad del
    tercer agente y con medio artículo escrito.
    """
    proveedores: Dict[str, Any] = {}
    for nombre in nombres:
        try:
            capacidad = get(nombre)
        except KeyError as error:
            raise MissingCapability(f"No hay ninguna capacidad llamada '{nombre}'") from error
        try:
            proveedores[nombre] = capacidad.resolve()
        except CapabilityNotAvailable as error:
            raise MissingCapability(str(error)) from error
    return CapabilityBundle(proveedores=proveedores)


def from_state(state: Mapping[str, Any]) -> Optional[CapabilityBundle]:
    """Bundle de la ejecución en curso, o `None` si se corre por el camino heredado."""
    bundle = state.get(CLAVE_ESTADO) if hasattr(state, "get") else None
    return bundle if isinstance(bundle, CapabilityBundle) else None


def provider(state: Mapping[str, Any], nombre: str, fallback: Any) -> Any:
    """Proveedor de `nombre` para esta ejecución, o `fallback` (el import directo).

    Es el punto por el que un agente deja de depender de un módulo concreto. El
    `fallback` mantiene vivo el camino de siempre mientras el flag esté en
    `adapters`, que es lo que permite comparar los dos sin borrar nada.
    """
    bundle = from_state(state)
    if bundle is not None and bundle.has(nombre):
        return bundle.get(nombre)
    return fallback
