#!/usr/bin/env python3
"""Mueve el RAG heredado al espacio por proyecto (SPEC-013 / T8.5 / AC6).

Antes de T8.5 no había proyecto en la capa RAG: todos los documentos vivían en la
colección que dijera el perfil del agente, normalmente `rag_docs`, mezclados. Tras
el cambio, cada proyecto lee `p_<id>__<bucket>` y **nada** lee las colecciones
heredadas — así que los documentos ya subidos dejan de verse hasta que se migran.

Atribución: los puntos heredados **no llevan proyecto**, así que no se puede
reconstruir a cuál pertenecía cada uno. Este script los asigna todos al proyecto
del sistema, que es la única lectura defendible:

* En una instancia de un solo proyecto —el caso normal hoy— es exacta.
* En una con varios, esos documentos ya se estaban filtrando entre proyectos: el
  destino correcto no existe. Asignarlos al del sistema **cierra** la fuga, y los
  demás proyectos vuelven a subir lo suyo. Fallar hacia el lado cerrado es lo
  contrario de lo que hacía el código anterior.

Es **idempotente** y no destructivo: copia y deja el original. Lo heredado se
borra a mano cuando se haya comprobado la migración (`--drop-legacy` lo hace).

Uso:
    python scripts/migrate_rag_namespaces.py                 # simulacro (por defecto)
    python scripts/migrate_rag_namespaces.py --apply
    python scripts/migrate_rag_namespaces.py --apply --drop-legacy
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

import httpx  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.models import ProjectModel  # noqa: E402
from app.platform.capabilities.rag import _local_rag_root  # noqa: E402
from app.platform.project_context import ProjectContext, is_project_collection  # noqa: E402

LOTE = 256


async def _proyecto_del_sistema() -> ProjectContext:
    try:
        async with AsyncSessionLocal() as session:
            resultado = await session.execute(
                select(ProjectModel).where(ProjectModel.is_system == True)  # noqa: E712
            )
            proyecto = resultado.scalars().first()
    except Exception as error:  # base sin migrar, credenciales, servidor caído…
        raise SystemExit(
            f"No se pudo leer la base de datos ({error.__class__.__name__}). "
            "Comprueba DATABASE_URL y que la aplicación haya arrancado al menos una vez."
        ) from error
    if proyecto is None:
        raise SystemExit(
            "No hay proyecto del sistema: arranca la aplicación una vez para que se cree."
        )
    return ProjectContext(project_id=proyecto.id, name=proyecto.name, is_system=True)


def _colecciones_locales_heredadas() -> list[str]:
    raiz = _local_rag_root()
    if not raiz.exists():
        return []
    return sorted(
        d.name for d in raiz.iterdir() if d.is_dir() and not is_project_collection(d.name)
    )


async def _colecciones_qdrant_heredadas(cliente: httpx.AsyncClient) -> list[str]:
    respuesta = await cliente.get("/collections")
    respuesta.raise_for_status()
    nombres = [c["name"] for c in respuesta.json()["result"]["collections"]]
    return sorted(n for n in nombres if not is_project_collection(n))


async def _copiar_coleccion_qdrant(
    cliente: httpx.AsyncClient, origen: str, destino: str, aplicar: bool
) -> int:
    info = await cliente.get(f"/collections/{origen}")
    if info.status_code != 200:
        return 0
    config = info.json()["result"]["config"]["params"]["vectors"]

    copiados = 0
    siguiente = None
    while True:
        cuerpo = {"limit": LOTE, "with_payload": True, "with_vector": True}
        if siguiente is not None:
            cuerpo["offset"] = siguiente
        pagina = await cliente.post(f"/collections/{origen}/points/scroll", json=cuerpo)
        pagina.raise_for_status()
        resultado = pagina.json()["result"]
        puntos = resultado.get("points", [])
        if not puntos:
            break
        if aplicar:
            await cliente.put(
                f"/collections/{destino}",
                json={"vectors": config},
            )
            subida = await cliente.put(
                f"/collections/{destino}/points?wait=true",
                json={"points": [
                    {"id": p["id"], "vector": p["vector"], "payload": p.get("payload", {})}
                    for p in puntos
                ]},
            )
            subida.raise_for_status()
        copiados += len(puntos)
        siguiente = resultado.get("next_page_offset")
        if siguiente is None:
            break
    return copiados


async def migrar(aplicar: bool, borrar_heredado: bool) -> int:
    destino_ctx = await _proyecto_del_sistema()
    print(f"Proyecto de destino: {destino_ctx.name} ({destino_ctx.project_id})")
    print(f"Modo: {'APLICAR' if aplicar else 'simulacro'}\n")

    # ── Respaldo local en disco ─────────────────────────────────────────────
    raiz = _local_rag_root()
    for nombre in _colecciones_locales_heredadas():
        destino = destino_ctx.collection(nombre)
        origen_dir = raiz / nombre
        ficheros = sorted(origen_dir.glob("*.json"))
        print(f"[local]  {nombre} → {destino}  ({len(ficheros)} documento(s))")
        if not aplicar:
            continue
        destino_dir = raiz / destino
        destino_dir.mkdir(parents=True, exist_ok=True)
        for fichero in ficheros:
            objetivo = destino_dir / fichero.name
            if objetivo.exists():
                continue  # idempotente: ya migrado
            objetivo.write_text(fichero.read_text(encoding="utf-8"), encoding="utf-8")
        if borrar_heredado:
            for fichero in ficheros:
                fichero.unlink()
            origen_dir.rmdir()

    # ── Qdrant ──────────────────────────────────────────────────────────────
    cabeceras = {"api-key": settings.QDRANT_API_KEY} if settings.QDRANT_API_KEY else {}
    try:
        async with httpx.AsyncClient(
            base_url=settings.QDRANT_URL, timeout=30.0, headers=cabeceras
        ) as cliente:
            for nombre in await _colecciones_qdrant_heredadas(cliente):
                destino = destino_ctx.collection(nombre)
                copiados = await _copiar_coleccion_qdrant(cliente, nombre, destino, aplicar)
                print(f"[qdrant] {nombre} → {destino}  ({copiados} punto(s))")
                if aplicar and borrar_heredado and copiados:
                    await cliente.delete(f"/collections/{nombre}")
    except httpx.RequestError as error:
        print(f"\n[aviso] Qdrant no responde ({error}); solo se migró el respaldo local.")

    if not aplicar:
        print("\nSimulacro. Repite con --apply para escribir.")
    elif not borrar_heredado:
        print("\nHecho. Lo heredado sigue en su sitio: comprueba y borra con --drop-legacy.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Escribe (por defecto: simulacro)")
    parser.add_argument(
        "--drop-legacy",
        action="store_true",
        help="Borra las colecciones heredadas tras copiarlas. Requiere --apply.",
    )
    args = parser.parse_args()
    if args.drop_legacy and not args.apply:
        parser.error("--drop-legacy necesita --apply")
    return asyncio.run(migrar(args.apply, args.drop_legacy))


if __name__ == "__main__":
    sys.exit(main())
