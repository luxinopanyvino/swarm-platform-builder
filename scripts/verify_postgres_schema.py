#!/usr/bin/env python3
"""Comprueba, contra una base Postgres real, lo que la CI con SQLite no puede ver.

Los tests de migraciones corren sobre SQLite, donde un enum es un VARCHAR sin
restricción: ahí `ALTER TYPE … ADD VALUE` no se ejecuta nunca. La migración
`0006_publication_gate` (SPEC-032) añade `REQUIRES_HUMAN_REVIEW` al enum nativo
`articlestatus` y crea claves ajenas con nombre; este script lo verifica después de
`alembic upgrade head` en Postgres.

Uso (lo ejecuta el job `migrations-postgres` de la CI):
    DATABASE_URL=postgresql+asyncpg://… python scripts/verify_postgres_schema.py
"""
from __future__ import annotations

import asyncio
import os
import sys

ESPERADO_ENUM = {"DRAFT", "IN_REVIEW", "APPROVED", "PUBLISHED", "REJECTED", "REQUIRES_HUMAN_REVIEW"}
COLUMNAS_ARTICULO = {"responsible_author_id", "approved_by", "approved_at", "approved_text_sha256"}
COLUMNAS_INFORME = {"id", "article_id", "run_id", "text_sha256", "criteria", "sources", "created_by", "created_at"}


def dsn(url: str) -> str:
    """`postgresql+asyncpg://…` → `postgresql://…`, lo que entiende asyncpg."""
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def problemas(enum_labels: set, cols_articulo: set, cols_informe: set, fks: set) -> list[str]:
    """Qué falta, en frases. Función pura para poder probarla sin Postgres."""
    out = []
    if falta := ESPERADO_ENUM - enum_labels:
        out.append(f"el enum articlestatus no tiene: {sorted(falta)}")
    if falta := COLUMNAS_ARTICULO - cols_articulo:
        out.append(f"articles no tiene las columnas: {sorted(falta)}")
    if falta := COLUMNAS_INFORME - cols_informe:
        out.append(f"publication_gate_reports no tiene las columnas: {sorted(falta)}")
    for fk in ("fk_articles_responsible_author_id_users", "fk_articles_approved_by_users"):
        if fk not in fks:
            out.append(f"falta la clave ajena {fk}")
    return out


async def main() -> int:
    import asyncpg

    url = os.environ.get("DATABASE_URL")
    if not url or "postgresql" not in url:
        print("DATABASE_URL debe apuntar a Postgres", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn(url))
    try:
        labels = {r["e"] for r in await conn.fetch("SELECT unnest(enum_range(NULL::articlestatus))::text AS e")}
        rows_articulo = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'articles'")
        rows_informe = await conn.fetch(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'publication_gate_reports'")
        fks = {r["conname"] for r in await conn.fetch(
            "SELECT conname FROM pg_constraint WHERE contype = 'f' AND conrelid = 'articles'::regclass")}
    finally:
        await conn.close()

    fallos = problemas(
        labels,
        {r["column_name"] for r in rows_articulo},
        {r["column_name"] for r in rows_informe},
        fks,
    )
    if fallos:
        print("ESQUEMA INCORRECTO en Postgres:")
        for f in fallos:
            print(f"  - {f}")
        return 1
    print(f"OK: articlestatus = {sorted(labels)}; columnas y claves ajenas de SPEC-032 presentes.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
