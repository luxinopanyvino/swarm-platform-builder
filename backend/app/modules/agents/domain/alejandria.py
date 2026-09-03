"""AlejandrIA Magazine, descrito como datos (SPEC-013 / T8.3).

Todo lo que el motor sabía de este proyecto —qué agentes hay, qué capacidades
compone cada uno y dónde vuelve el bucle de revisión— estaba escrito **dentro**
del orquestador. Aquí queda como declaración de un proyecto concreto, que es lo
que T8.4 moverá a `projects/alejandria-magazine/template.yaml`.

Mientras tanto ya cumple su función: el motor no menciona a `revisor` ni a
`redactor` en ningún sitio, así que otro proyecto puede declarar su propio bucle
—o no tener ninguno— sin tocarlo.
"""
from __future__ import annotations

from app.platform.engine.agents import AgentSpec, register_agent
from app.platform.engine.routing import ReviewLoop

#: El bucle editorial: el revisor devuelve el borrador al redactor mientras no
#: llegue a 80, con un máximo de 3 vueltas. `retry_targets` es a dónde volver
#: cuando la persona usuaria sube una fuente nueva: al investigador si está en el
#: flujo, para que la fuente entre en la investigación y en las citas; si no, al
#: redactor, que al menos la usará como contexto.
BUCLE_REVISION = ReviewLoop(
    reviewer="revisor",
    on_reject="redactor",
    threshold=80.0,
    max_loops=3,
    retry_targets=("investigador", "redactor"),
)

BUCLES = (BUCLE_REVISION,)

#: Los cinco agentes editoriales. `requires` nombra las capacidades que compone
#: cada uno; es lo que se le resuelve e inyecta cuando el motor corre en modo
#: `capabilities`. El investigador pide `rag_results` y no `rag` porque construye
#: citas y necesita los metadatos, no un bloque de texto.
AGENTES = (
    AgentSpec(
        name="investigador",
        entrypoint="app.modules.agents.adapters.investigador:run_investigador",
        requires=("rag_results", "llm"),
        description="Busca fuentes en la base de conocimiento y sintetiza el material.",
    ),
    AgentSpec(
        name="redactor",
        entrypoint="app.modules.agents.adapters.redactor:run_redactor",
        requires=("rag", "llm", "llm_stream"),
        description="Escribe el borrador a partir de la investigación y del feedback.",
    ),
    AgentSpec(
        name="revisor",
        entrypoint="app.modules.agents.adapters.revisor:run_revisor",
        requires=("llm",),
        description="Evalúa el borrador y decide si vuelve al redactor.",
    ),
    AgentSpec(
        name="formateador",
        entrypoint="app.modules.agents.adapters.formateador:run_formateador",
        requires=("llm",),
        description="Aplica el formato científico y construye las referencias.",
    ),
    AgentSpec(
        name="publicador",
        entrypoint="app.modules.agents.adapters.publicador:run_publicador",
        requires=("format",),
        description="Persiste el artículo final y genera la maquetación imprimible.",
    ),
)


def register() -> None:
    """Da de alta el proyecto en el motor. Idempotente."""
    for agente in AGENTES:
        register_agent(agente)
