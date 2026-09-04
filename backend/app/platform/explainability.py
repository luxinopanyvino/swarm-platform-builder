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


# ── Lectura de la traza (SPEC-014 / T9.2 / AC2) ─────────────────────────────
#
# La otra mitad del módulo. Escribir la traza es anotar lo que solo sabe quien lo
# produce; leerla es contestar «por qué salió esto», y esa pregunta no se responde
# con la tabla en crudo: hay que separar ejecuciones y agregar fuentes.
#
# Funciones puras sobre una lista de pasos, a propósito: es la lógica que más
# fácil se equivoca y así se prueba sin base de datos ni pipeline.

def group_executions(pasos: List[Any]) -> List[List[Any]]:
    """Parte los pasos —en orden cronológico— en ejecuciones del pipeline.

    Un artículo se puede reejecutar, y entonces su traza tiene los pasos de
    varias ejecuciones **en la misma tabla**. Ordenarlos por `step_index` los
    entrelazaría: dos ejecuciones tienen las dos un paso 0, un paso 1… y el panel
    contaría una historia que no ocurrió.

    Lo que las separa es que `step_index` **vuelve a 0**: el orquestador lo
    reinicia en cada ejecución nueva. Una reanudación (`resume`) no reinicia
    —continúa desde el checkpoint—, así que sigue la numeración y aparece como lo
    que es: la misma ejecución, terminada en un segundo intento.

    No se agrupa por `run_id` porque no es lo que se cree: `log_run_start` mina
    uno **por paso**, no por ejecución. Ni por `correlation_id`, que puede faltar.
    """
    ejecuciones: List[List[Any]] = []
    for paso in pasos:
        if not ejecuciones or (paso.step_index == 0 and ejecuciones[-1]):
            ejecuciones.append([])
        ejecuciones[-1].append(paso)
    return ejecuciones


def aggregate_sources(pasos: Iterable[Any]) -> List[Dict[str, Any]]:
    """Fuentes RAG de todos los pasos, agrupadas por documento.

    Mismo criterio que al recogerlas dentro de un paso: se conserva el **mejor**
    score y se unen los fragmentos, porque la pregunta es «¿de qué documentos
    salió esto?». Se añade `used_by`: qué agentes lo recuperaron, que es lo que
    distingue una fuente que solo vio el investigador de una que además usó el
    redactor al ampliar el borrador.
    """
    agregadas: Dict[str, Dict[str, Any]] = {}
    for paso in pasos:
        for fuente in (paso.rag_sources or []):
            if not isinstance(fuente, dict):
                continue
            doc_id = str(fuente.get("doc_id") or "")
            if not doc_id:
                continue
            actual = agregadas.setdefault(doc_id, {
                "doc_id": doc_id, "title": None, "authors": None,
                "collection": None, "score": 0.0, "chunk_ids": [], "used_by": [],
            })
            for clave in ("title", "authors", "collection"):
                if actual[clave] is None and fuente.get(clave):
                    actual[clave] = fuente[clave]
            try:
                puntuacion = float(fuente.get("score") or 0.0)
            except (TypeError, ValueError):
                puntuacion = 0.0
            actual["score"] = max(actual["score"], puntuacion)
            for chunk in (fuente.get("chunk_ids") or []):
                if chunk not in actual["chunk_ids"]:
                    actual["chunk_ids"].append(chunk)
            if paso.agent_name not in actual["used_by"]:
                actual["used_by"].append(paso.agent_name)

    # De mejor a peor score: la fuente que más pesó, primero.
    return sorted(agregadas.values(), key=lambda f: f["score"], reverse=True)


def totals_of(pasos: List[Any]) -> Dict[str, Any]:
    """Lo que costó lo que se está leyendo."""
    agentes: List[str] = []
    for paso in pasos:
        if paso.agent_name not in agentes:
            agentes.append(paso.agent_name)
    return {
        "steps": len(pasos),
        "agents": agentes,
        "tokens_in": sum(paso.tokens_in or 0 for paso in pasos),
        "tokens_out": sum(paso.tokens_out or 0 for paso in pasos),
        "latency_ms": round(sum(paso.latency_ms or 0.0 for paso in pasos), 2),
        "loops": max((paso.iteration or 0 for paso in pasos), default=0),
        "failed_steps": sum(1 for paso in pasos if paso.status != "completed"),
    }
