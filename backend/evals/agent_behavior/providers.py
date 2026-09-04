"""De dónde sale la salida que se evalúa (SPEC-014 / T9.3 / AC3).

AC3 pide un informe **reproducible** y «sin depender de servicios externos no
declarados». Eso son dos requisitos que tiran en direcciones distintas: evaluar
el comportamiento real exige llamar al modelo configurado, y un modelo generativo
no da dos veces lo mismo — ni está disponible en la CI, donde no hay Ollama ni
API key.

Se resuelve con dos modos **explícitos**, y el informe registra cuál se usó:

* **`live`** — llama al agente de la plataforma tal y como corre en producción,
  con su modelo y sus parámetros resueltos por el dispatcher. Es lo que mide el
  comportamiento de verdad. No es determinista, y por eso el informe registra
  modelo y parámetros: dos ejecuciones son comparables porque se sabe con qué se
  hicieron, no porque salga lo mismo.
* **`replay`** — reproduce la salida grabada en el dataset. No evalúa al modelo:
  evalúa **las métricas y el harness**, de forma exactamente repetible. Es lo que
  permite el gate de CI de T9.5 y lo que hace que un cambio en una métrica se vea
  como lo que es.

Confundir los dos sería lo peor que podría pasarle a este harness —un `replay`
presentado como evidencia de que el agente va bien—, así que el modo va en el
informe, en el nombre del fichero y en el resumen de la consola.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Protocol, Tuple

from evals.agent_behavior.models import EvalCase

MODO_LIVE = "live"
MODO_REPLAY = "replay"


class Provider(Protocol):
    """Produce la salida de un caso y lo que costó."""

    mode: str

    async def run(self, caso: EvalCase) -> Tuple[str, Dict[str, Any]]:
        ...


class ReplayProvider:
    """Reproduce la salida grabada en el dataset."""

    mode = MODO_REPLAY

    async def run(self, caso: EvalCase) -> Tuple[str, Dict[str, Any]]:
        # Un agente que decide y no escribe —el revisor— no tiene salida de
        # texto: su caso graba `recorded_decision` y `recorded_output` vacío.
        if caso.recorded_output is None and caso.recorded_decision is not None:
            return "", {**dict(caso.recorded_usage), "latency_ms": 0.0,
                        "decision": caso.recorded_decision}
        if caso.recorded_output is None:
            raise RuntimeError(
                f"El caso '{caso.id}' no trae `recorded_output`: no se puede reproducir. "
                "Ejecútalo en modo `live` o graba su salida."
            )
        uso = dict(caso.recorded_usage)
        # La latencia de leer un fichero no es la del agente: se deja a 0 y la
        # métrica de presupuesto se salta en vez de puntuar un número inventado.
        uso.setdefault("latency_ms", 0.0)
        uso["decision"] = caso.recorded_decision
        return caso.recorded_output, uso


class PlatformProvider:
    """Ejecuta el agente **de la plataforma**, con su modelo y sus parámetros.

    Reutiliza el runner real (`platform/engine/agents.py`), no una copia: si el
    harness llamara al LLM por su cuenta, mediría algo parecido al agente pero no
    al agente, y las regresiones que importan viven justo en esa diferencia
    (prompt, parámetros, capacidades inyectadas).
    """

    mode = MODO_LIVE

    def __init__(self, agent: str):
        self.agent = agent

    async def run(self, caso: EvalCase) -> Tuple[str, Dict[str, Any]]:
        from app.modules.agents.domain import alejandria
        from app.platform import explainability
        from app.platform.engine.agents import resolve_runner

        alejandria.register()
        runner = resolve_runner(self.agent)

        estado: Dict[str, Any] = {
            "title": "", "keywords": [], "research_data": "", "draft_text": "",
            "feedback": [], "agent_settings": {}, "loop_count": 0,
            # Sin canal de decisión: el harness no puede contestar a un HITL, y
            # dejarlo abierto colgaría la evaluación esperando a nadie.
            "_log": lambda *_a, **_k: None,
            "_emit_token": lambda *_a, **_k: None,
        }
        estado.update(caso.input)

        inicio = time.perf_counter()
        with explainability.collecting() as acumulador:
            salida = await runner(estado)
        latencia = (time.perf_counter() - inicio) * 1000

        texto = explainability.output_text(salida) or ""
        return texto, {
            "tokens_in": acumulador.tokens_in,
            "tokens_out": acumulador.tokens_out,
            "latency_ms": latencia,
            # La decisión sale por el mismo lector que usa la traza de T9.1, no
            # por uno propio: si el revisor cambia de forma, cambia en un sitio.
            # Sin esto el revisor sería inevaluable — no produce texto.
            "decision": explainability.decision_of(salida),
            "raw_output": salida,
        }


def build(mode: str, agent: str) -> Provider:
    if mode == MODO_REPLAY:
        return ReplayProvider()
    if mode == MODO_LIVE:
        return PlatformProvider(agent)
    raise ValueError(f"Modo desconocido '{mode}'. Usa '{MODO_LIVE}' o '{MODO_REPLAY}'.")
