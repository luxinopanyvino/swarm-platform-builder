"""Contexto de proyecto y espacio de nombres RAG (SPEC-013 / T8.5 / AC6).

AC6 pide que dos proyectos con documentos RAG distintos no se vean el uno al
otro. Antes de esto no había **ninguna** noción de proyecto en la capa RAG:

* La colección de Qdrant salía del **perfil del agente** (`rag_collection`, por
  defecto `settings.QDRANT_COLLECTION` = `rag_docs`). Dos proyectos creados desde
  la misma plantilla nacen con el mismo perfil, así que sus documentos caían en la
  **misma** colección, en el **mismo** bucket `agent_name`. El pipeline de uno
  recuperaba los documentos del otro.
* Y `rag_collection` es un **campo que escribe la persona usuaria** en el editor de
  agentes: aunque cada proyecto tuviera su colección, bastaba con teclear la del
  vecino para leerla.

De ahí la forma de la solución: el nombre real de la colección **se deriva, no se
recibe**. Lo que el perfil aporta es un *bucket* dentro del proyecto, y este módulo
es el único sitio que compone el nombre final. Un bucket no puede salirse de su
prefijo, así que el aislamiento no depende de que nadie olvide un filtro.

`__library__` —la biblioteca compartida entre agentes— queda compartida **dentro
del proyecto** y no entre proyectos, que es lo que AC6 exige y lo que la palabra
«compartida» debía haber significado desde el principio.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

#: Prefijo de toda colección con dueño. Sirve además para distinguir de un vistazo
#: las colecciones nuevas de las heredadas al mirar Qdrant en producción.
PREFIJO_PROYECTO = "p_"

#: Separador entre el proyecto y el bucket que pide el perfil del agente.
SEPARADOR = "__"

#: Colecciones anteriores a T8.5, sin proyecto. Se conservan legibles solo para el
#: proyecto del sistema (ver `resolve_collection`), porque el contenido que hay en
#: ellas no se puede atribuir retroactivamente a ningún proyecto.
_MAX_BUCKET = 48

_NO_PERMITIDO = re.compile(r"[^a-z0-9_-]+")

logger = logging.getLogger(__name__)


def sanitize_bucket(nombre: Optional[str]) -> str:
    """Reduce el `rag_collection` del perfil a un identificador inofensivo.

    Es texto que escribe la persona usuaria: sin esto, un `../` o un nombre con
    barras podría apuntar fuera del proyecto, tanto en Qdrant como en el
    almacenamiento local de respaldo, que escribe directorios en disco.
    """
    limpio = _NO_PERMITIDO.sub("_", (nombre or "").strip().lower()).strip("_-")
    return limpio[:_MAX_BUCKET] or "rag_docs"


@dataclass(frozen=True)
class ProjectContext:
    """Proyecto bajo el que se ejecuta una petición o un pipeline.

    Inmutable a propósito: se propaga por el grafo de agentes y por las llamadas a
    las capacidades, y un contexto que alguien pueda reescribir a mitad de camino
    no aislaría nada.
    """

    project_id: UUID
    name: str = ""
    is_system: bool = False

    @property
    def slug(self) -> str:
        """Fragmento estable e inofensivo del proyecto para nombrar recursos."""
        return f"{PREFIJO_PROYECTO}{self.project_id.hex}"

    def collection(self, bucket: Optional[str] = None) -> str:
        """Colección real para un bucket pedido por el perfil de un agente."""
        return f"{self.slug}{SEPARADOR}{sanitize_bucket(bucket)}"

    def owns_collection(self, nombre: str) -> bool:
        return nombre.startswith(f"{self.slug}{SEPARADOR}")


def is_project_collection(nombre: str) -> bool:
    """¿El nombre pertenece al esquema con proyecto (y no a una colección heredada)?"""
    return nombre.startswith(PREFIJO_PROYECTO) and SEPARADOR in nombre


def bucket_of(nombre: str) -> str:
    """Bucket legible dentro de una colección con proyecto (para la interfaz)."""
    if not is_project_collection(nombre):
        return nombre
    return nombre.split(SEPARADOR, 1)[1]


def resolve_collection(context: Optional[ProjectContext], bucket: Optional[str]) -> str:
    """Nombre de colección para `bucket` dentro de `context`.

    Sin contexto no se inventa un proyecto: se cae al nombre heredado. Eso solo
    ocurre en caminos que no tienen proyecto (el `ensure_collection` de arranque),
    y mantenerlo explícito evita que un `None` silencioso mande documentos de un
    proyecto a la colección común.
    """
    if context is None:
        return sanitize_bucket(bucket)
    return context.collection(bucket)


def context_from_state(state) -> Optional[ProjectContext]:
    """`ProjectContext` a partir del estado del grafo de agentes.

    El estado solo lleva el `project_id`: el nombre y `is_system` no hacen falta
    para resolver colecciones, y arrastrar el objeto entero por los checkpoints de
    LangGraph obligaría a serializarlo.
    """
    project_id = state.get("project_id") if hasattr(state, "get") else None
    if project_id is None:
        return None
    if not isinstance(project_id, UUID):
        project_id = UUID(str(project_id))
    return ProjectContext(project_id=project_id)


def collection_for_state(state, bucket: Optional[str]) -> str:
    """Colección RAG que le toca a un agente según el proyecto de su ejecución.

    Un único sitio para los tres adapters. Sin proyecto en el estado se cae al
    nombre heredado y **se avisa**: es el camino que existía antes de T8.5 y solo
    debería quedar en pruebas o en ejecuciones anteriores a esta versión, nunca en
    una lanzada por el endpoint de ejecución, que ya exige proyecto.
    """
    context = context_from_state(state)
    if context is None:
        logger.warning(
            "Ejecución sin project_id: la colección RAG cae al nombre heredado %r "
            "y no queda aislada por proyecto (SPEC-013 / T8.5 / AC6)",
            sanitize_bucket(bucket),
        )
    return resolve_collection(context, bucket)
