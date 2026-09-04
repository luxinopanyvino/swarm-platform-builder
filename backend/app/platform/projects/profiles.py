"""Localización de perfiles `.agent.md` (SPEC-013 / T8.4 / AC4).

Había **cuatro** sitios distintos haciendo lo mismo a mano:

```python
_AGENTS_DIRS = [Path("app/agents"), Path("../app/agents")]
```

en `adapters/generic.py`, `shared/agents_seed.py`, `platform/llm.py` y
`routers/agents.py`. Son rutas relativas al **directorio de trabajo**, así que el
mismo código encuentra los perfiles al arrancar con `uvicorn` desde `backend/` y
no los encuentra desde la raíz del repo o desde un contenedor con otro
`WORKDIR`. Y cuando no los encuentra no falla: cae a un modelo por defecto y a un
prompt genérico, así que el síntoma aparece lejos de la causa.

Aquí la búsqueda se hace **una vez** y sobre los proyectos empaquetados, cuya raíz
sale del propio paquete. `app/agents/` ya no se referencia desde ningún sitio,
que es lo que pide AC4.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from app.platform.projects import loader

logger = logging.getLogger(__name__)

SUFIJO = ".agent.md"


@lru_cache(maxsize=None)
def _indice() -> Dict[str, Path]:
    """nombre de agente → ruta de su perfil, sobre todos los proyectos.

    Incluye los `.agent.md` que hay en el directorio del proyecto aunque su
    plantilla no los declare: son agentes personalizados que alguien dejó ahí, y
    dejar de encontrarlos rompería flujos que hoy funcionan. Lo que sí cambia es
    que ya no se siembran como agentes de serie (ver `agents_seed`).
    """
    encontrados: Dict[str, Path] = {}
    for slug in loader.available_slugs():
        directorio = loader.PROJECTS_ROOT / slug / "agents"
        if not directorio.is_dir():
            continue
        for fichero in sorted(directorio.glob(f"*{SUFIJO}")):
            encontrados.setdefault(fichero.name[: -len(SUFIJO)], fichero)
    return encontrados


def agents_dir(slug: str = "alejandria-magazine") -> Path:
    """Directorio de perfiles de un proyecto empaquetado."""
    return loader.PROJECTS_ROOT / slug / "agents"


def find(agent_name: str) -> Optional[Path]:
    """Ruta del perfil de `agent_name`, o `None` si no hay ninguno."""
    return _indice().get(agent_name)


def reset_cache() -> None:
    """Vacía el índice (los tests crean proyectos temporales)."""
    _indice.cache_clear()
    loader.load.cache_clear()
