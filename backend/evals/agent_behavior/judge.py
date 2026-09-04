"""Juez de las métricas asistidas (SPEC-014 / T9.4 / AC4).

AC4 pide dos métricas que no se pueden calcular con una expresión regular:
**coherencia** del texto y **calibración** del score del revisor. La primera
necesita un juicio; la segunda, una referencia.

Tres decisiones, y las tres vienen de la spec:

* **El juez es un modelo de la plataforma**, no un servicio externo de
  evaluación (§4.2). Se llama por el mismo dispatcher que usan los agentes, así
  que juzga con el `LLM_PROVIDER` activo y aparece en el informe como lo que es.
* **Rúbrica fija y `temperature=0`** (§5). Un juez que cambia de criterio entre
  ejecuciones convierte el gate de T9.5 en un generador de rojos aleatorios: la
  métrica dejaría de medir al agente para medir al juez.
* **En `replay` no se llama a nadie.** El veredicto se graba en el dataset igual
  que la salida, y si no está, la métrica **se salta con motivo**. Inventar un
  juicio para que el caso puntúe sería exactamente la mentira que este harness
  existe para no contar.

Quién llama al juez es el runner, no la métrica: ahí es donde se sabe el modo, y
así las métricas siguen siendo funciones puras sobre lo ya obtenido — el mismo
reparto que en T9.1, donde quien conoce el dato lo anota y quien lo consume solo
lo lee.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Protocol

from evals.agent_behavior.models import CaseResult, EvalCase

MODO_LIVE = "live"
MODO_REPLAY = "replay"

#: La rúbrica es **parte del contrato de la métrica**: cambiarla cambia lo que
#: significan los números de todos los informes anteriores. Si se toca, sube la
#: versión de los datasets que la usan.
RUBRICA_VERSION = "1"

RUBRICA = """\
Eres un evaluador de textos científicos. Puntúa la COHERENCIA del texto de 0 a 100
aplicando exactamente estos criterios, sin añadir otros:

- 0-20: se contradice, cambia de tema o afirma cosas sin ninguna conexión.
- 21-40: el tema se mantiene pero las secciones no se relacionan entre sí.
- 41-60: hay hilo argumental, con saltos o afirmaciones sin apoyo.
- 61-80: argumentación consistente; las secciones se conectan; algún hueco menor.
- 81-100: cada sección se apoya en la anterior y las conclusiones se siguen de lo expuesto.

Juzga SOLO la coherencia interna. No premies ni penalices la extensión, el estilo,
el formato de las citas ni si el tema te parece interesante.

Devuelve únicamente un objeto JSON, sin texto alrededor ni bloques de código:
{"score": <entero 0-100>, "reason": "<una frase>"}
"""


class Judge(Protocol):
    mode: str

    async def assess(self, caso: EvalCase, resultado: CaseResult) -> Optional[Dict[str, Any]]:
        ...


def _parsear_veredicto(crudo: str) -> Dict[str, Any]:
    """Saca el JSON del veredicto. Un modelo lo envuelve en prosa a menudo."""
    encontrado = re.search(r"\{.*\}", crudo or "", re.DOTALL)
    if not encontrado:
        raise ValueError(f"el juez no devolvió JSON: {(crudo or '')[:120]!r}")
    datos = json.loads(encontrado.group(0))
    puntuacion = datos.get("score")
    if not isinstance(puntuacion, (int, float)) or isinstance(puntuacion, bool):
        raise ValueError(f"el veredicto no trae 'score' numérico: {datos!r}")
    return {
        "score": max(0.0, min(100.0, float(puntuacion))),
        "reason": str(datos.get("reason") or ""),
        "rubric_version": RUBRICA_VERSION,
    }


class RecordedJudge:
    """Reproduce el veredicto grabado en el caso. No llama a ningún modelo."""

    mode = MODO_REPLAY

    async def assess(self, caso: EvalCase, resultado: CaseResult) -> Optional[Dict[str, Any]]:
        return caso.recorded_judgement


class PlatformJudge:
    """Juzga con el modelo de la plataforma, con la rúbrica fija y sin creatividad."""

    mode = MODO_LIVE

    def __init__(self, model: Optional[str] = None):
        self.model = model

    async def assess(self, caso: EvalCase, resultado: CaseResult) -> Optional[Dict[str, Any]]:
        texto = (resultado.output or "").strip()
        if not texto:
            return None

        from app.platform.llm import call_llm

        crudo = await call_llm(
            f"{RUBRICA}\n\nTexto a evaluar:\n\n{texto}\n\nJSON:",
            model=self.model,
            temperature=0,
        )
        veredicto = _parsear_veredicto(crudo)
        veredicto["judge_model"] = self.model or ""
        return veredicto


def needs_judgement(caso: EvalCase) -> bool:
    """¿Este caso declara que hay que juzgarlo? Solo lo pide quien lo dice."""
    return "min_coherence" in (caso.expect or {})


def build(mode: str, model: Optional[str] = None) -> Judge:
    if mode == MODO_REPLAY:
        return RecordedJudge()
    if mode == MODO_LIVE:
        return PlatformJudge(model)
    raise ValueError(f"Modo desconocido '{mode}'. Usa '{MODO_LIVE}' o '{MODO_REPLAY}'.")
