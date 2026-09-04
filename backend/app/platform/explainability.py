"""Recolección de la traza de explicabilidad (SPEC-014 / T9.1 / AC1).

AC1 pide, por cada paso de agente: modelo y parámetros, resumen de entrada y
salida, **fuentes RAG citadas** con `doc_id`, `chunk_ids` y score, tokens in/out,
latencia y, cuando aplique, la decisión con su *rationale*.

Tres de esos datos no están donde se escribe el paso:

* Los **tokens** solo los conoce el proveedor del LLM, dentro de `llm.py`, que ni
  siquiera sabe qué agente está corriendo.
* Las **fuentes RAG** solo las conoce la capacidad de RAG, y el agente que la
  llama se queda con el texto ya montado: las citas que acaban en el artículo son
  una elaboración posterior, no lo que se recuperó.
* La **decisión** la produce el agente y viaja en su salida.

Podrían pasarse por parámetro hasta el orquestador, pero eso significa cambiar la
firma de todo lo que hay en medio y, sobre todo, que un agente nuevo no aparezca
en la traza hasta que alguien se acuerde de instrumentarlo. Aquí se recogen con
**variables de contexto**, igual que `current_agent_ctx` para las métricas
(T5.2): quien produce el dato lo anota donde está, y el orquestador lo recoge al
cerrar el paso. Un agente nuevo queda trazado sin tocarlo.

Nada de esto puede tumbar una ejecución: recoger la traza es observabilidad, y
observar no puede romper lo observado.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

#: Cuánto texto de entrada/salida se guarda. La traza explica una ejecución, no
#: es un segundo almacén del artículo: el cuerpo completo ya está en `articles`.
MAX_TEXTO = 4000


@dataclass
class StepAccumulator:
    """Lo que se va anotando mientras corre un paso."""

    tokens_in: int = 0
    tokens_out: int = 0
    rag_sources: List[Dict[str, Any]] = field(default_factory=list)


_paso: ContextVar[Optional[StepAccumulator]] = ContextVar("explain_step", default=None)


def current() -> Optional[StepAccumulator]:
    return _paso.get()


@contextmanager
def collecting():
    """Abre un acumulador para el paso en curso y lo devuelve al cerrarlo.

    Es un `ContextVar`, así que cada ejecución concurrente tiene el suyo: dos
    pipelines a la vez no se mezclan las fuentes ni los tokens.
    """
    acumulador = StepAccumulator()
    token = _paso.set(acumulador)
    try:
        yield acumulador
    finally:
        _paso.reset(token)


def record_tokens(entrada: Optional[int], salida: Optional[int]) -> None:
    """Suma los tokens de una llamada al LLM al paso en curso.

    Se **suma** y no se asigna porque un paso puede llamar al LLM varias veces
    (el redactor amplía el borrador si se queda corto), y el coste del paso es el
    total.
    """
    acumulador = _paso.get()
    if acumulador is None:
        return
    try:
        acumulador.tokens_in += int(entrada or 0)
        acumulador.tokens_out += int(salida or 0)
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudieron anotar los tokens del paso", exc_info=True)


def record_rag_hits(collection: str, resultados: Iterable[Dict[str, Any]]) -> None:
    """Anota lo que una búsqueda RAG devolvió de verdad.

    Se agrupa por documento y se acumulan sus `chunk_ids`: la pregunta que
    responde la traza es «¿de qué documentos salió esto?», y una lista de
    fragmentos sueltos obliga a reconstruirlo a mano.
    """
    acumulador = _paso.get()
    if acumulador is None:
        return
    try:
        por_doc: Dict[str, Dict[str, Any]] = {
            fuente["doc_id"]: fuente for fuente in acumulador.rag_sources
        }
        for item in resultados or []:
            doc_id = str(item.get("doc_id") or "")
            if not doc_id:
                continue
            fuente = por_doc.get(doc_id)
            if fuente is None:
                fuente = {
                    "doc_id": doc_id,
                    "collection": collection,
                    "title": (item.get("doc_title") or item.get("filename") or "").strip(),
                    "authors": (item.get("doc_authors") or "").strip(),
                    "chunk_ids": [],
                    "score": None,
                }
                por_doc[doc_id] = fuente
                acumulador.rag_sources.append(fuente)

            chunk_id = item.get("chunk_id")
            if chunk_id is not None and chunk_id not in fuente["chunk_ids"]:
                fuente["chunk_ids"].append(chunk_id)

            score = item.get("score")
            if score is not None:
                # El mejor fragmento representa al documento: es el que decidió
                # que ese documento entrara en el contexto.
                anterior = fuente["score"]
                fuente["score"] = score if anterior is None else max(anterior, score)
    except Exception:  # pragma: no cover - defensivo
        logger.debug("No se pudieron anotar las fuentes RAG del paso", exc_info=True)


# ── Construcción del registro ───────────────────────────────────────────────

def _recortar(texto: Any) -> Optional[str]:
    if texto is None:
        return None
    texto = str(texto)
    if len(texto) <= MAX_TEXTO:
        return texto
    return texto[:MAX_TEXTO] + f"\n…[recortado, {len(texto)} caracteres en total]"


def input_digest(state: Dict[str, Any]) -> str:
    """Resumen legible de con qué entró el agente al paso.

    No es el prompt: el prompt lo compone cada agente y llevarlo entero
    duplicaría el borrador y las fuentes en cada fila. Esto es lo que permite
    entender la entrada sin reconstruirla.
    """
    partes = [
        f"título: {state.get('title') or '—'}",
        f"palabras clave: {', '.join(state.get('keywords') or []) or '—'}",
        f"investigación: {len((state.get('research_data') or '').split())} palabras",
        f"borrador: {len((state.get('draft_text') or '').split())} palabras",
        f"vuelta del bucle: {state.get('loop_count', 0)}",
    ]
    feedback = state.get("feedback") or []
    if feedback:
        partes.append(f"feedback recibido: {len(feedback)} comentario(s)")
    return " · ".join(partes)


def output_text(salida: Dict[str, Any]) -> Optional[str]:
    """El texto que el paso produjo, sea cual sea el campo en que lo deje."""
    for clave in ("formatted_text", "draft_text", "research_data", "published_url"):
        valor = salida.get(clave)
        if valor:
            return _recortar(valor)
    return None


def decision_of(salida: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Decisión del paso, si la hay: score, coherencia y desenlace del HITL.

    Solo la tienen los pasos que **deciden** —hoy el revisor—; para el resto la
    columna queda a `NULL`, que dice más que un diccionario vacío.
    """
    claves = ("approval_score", "coherent", "user_decision")
    if not any(clave in salida for clave in claves):
        return None
    return {
        "score": salida.get("approval_score"),
        "coherent": salida.get("coherent"),
        "hitl_outcome": salida.get("user_decision"),
    }


def rationale_of(salida: Dict[str, Any]) -> Optional[str]:
    """El porqué de la decisión, en palabras: el feedback del revisor."""
    feedback = salida.get("feedback")
    if not feedback:
        return None
    if isinstance(feedback, str):
        return _recortar(feedback)
    return _recortar("\n".join(f"- {item}" for item in feedback))


def params_of(agent_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Parámetros con los que corrió el agente, de sus ajustes de ejecución."""
    ajustes = (state.get("agent_settings") or {}).get(agent_name) or {}
    interesantes = (
        "temperature", "num_ctx", "target_word_count", "output_language",
        "scientific_format", "rag_collection", "rag_top_k", "graph_rag_enabled",
        "semantic_search_enabled",
    )
    return {clave: ajustes[clave] for clave in interesantes if clave in ajustes}
