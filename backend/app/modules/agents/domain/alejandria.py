"""AlejandrIA Magazine: puente hacia su plantilla (SPEC-013 / T8.4).

En T8.3 este módulo **era** la definición del proyecto: sus cinco agentes, sus
capacidades y su bucle, escritos en Python. T8.4 los mueve a
`backend/projects/alejandria-magazine/template.yaml`, que es donde tienen que
estar para que crear un proyecto sea copiar un directorio y no editar código.

Lo que queda aquí es la lectura de esa plantilla, con los mismos nombres que
antes para que nada de lo que ya la usaba tenga que cambiar. Cuando exista más de
un proyecto, `register_project(slug)` sustituye a `register()` sin más.
"""
from __future__ import annotations

import logging
from typing import Tuple

from app.platform.engine.graph import GraphSpec
from app.platform.engine.routing import ReviewLoop
from app.platform.projects import loader

logger = logging.getLogger(__name__)

SLUG = "alejandria-magazine"


def package():
    """Plantilla cargada y validada (se cachea en el *loader*)."""
    return loader.load(SLUG)


def graph_spec() -> GraphSpec:
    """Secuencia y bucles del proyecto, tal y como los declara su `template.yaml`."""
    return package().graph


def loops() -> Tuple[ReviewLoop, ...]:
    return package().graph.loops


def review_loop() -> ReviewLoop:
    """El bucle editorial (revisor → redactor).

    Se expone aparte porque `use_cases` mantiene `route_after_revisor` y
    `MAX_REVIEW_LOOPS` como alias de compatibilidad.
    """
    bucles = loops()
    if not bucles:
        raise LookupError(f"La plantilla de '{SLUG}' no declara ningún bucle de revisión")
    return bucles[0]


def register() -> None:
    """Da de alta los agentes de la plantilla en el motor. Idempotente."""
    package().register()
