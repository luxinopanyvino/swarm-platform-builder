#!/usr/bin/env python3
"""Sincroniza los artículos PUBLICADOS desde la BD local hacia Hostinger.

Lee la base de datos local de la plataforma (Postgres por defecto, vía la
configuración del backend) y envía los artículos en estado PUBLISHED al
endpoint PHP de ingesta (`api/ingest.php`) protegido por token.

Uso:
    # variables de entorno requeridas
    export HOSTINGER_INGEST_URL="https://tudominio.com/api/ingest.php"
    export HOSTINGER_INGEST_TOKEN="<el-mismo-token-que-en-db.php>"

    python scripts/publish_to_hostinger.py            # envía todos los publicados
    python scripts/publish_to_hostinger.py --dry-run  # solo muestra qué enviaría

Sin dependencias extra: usa la SQLAlchemy/asyncpg del backend y urllib (stdlib).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Permitir importar el paquete `app` del backend.
BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from sqlalchemy import select  # noqa: E402

from app.models import ArticleModel, ArticleStatus  # noqa: E402
from app.shared.database import AsyncSessionLocal  # noqa: E402


def _iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def _to_public(a: ArticleModel) -> dict:
    """Mapea un artículo local al subconjunto público que guarda MySQL."""
    return {
        "id": str(a.id),
        "title": a.title,
        "body": a.body or "",
        "abstract": a.abstract or None,
        "authors": a.authors if isinstance(a.authors, list) else [],
        "cover_url": a.cover_url or None,
        "published_at": _iso(a.published_at),
        "updated_at": _iso(a.updated_at),
    }


async def _fetch_published() -> list[dict]:
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ArticleModel)
            .where(ArticleModel.status == ArticleStatus.PUBLISHED)
            .order_by(ArticleModel.published_at.desc())
        )
        result = await session.execute(stmt)
        return [_to_public(a) for a in result.scalars().all()]


def _post(url: str, token: str, payload: list[dict]) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Ingest-Token": token,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="No envía nada; solo lista los artículos publicados.")
    args = parser.parse_args()

    articles = asyncio.run(_fetch_published())
    print(f"Artículos publicados encontrados: {len(articles)}")

    if args.dry_run:
        for a in articles:
            print(f"  - {a['id']}  {a['title']}")
        return 0

    if not articles:
        print("Nada que sincronizar.")
        return 0

    url = os.environ.get("HOSTINGER_INGEST_URL")
    token = os.environ.get("HOSTINGER_INGEST_TOKEN")
    if not url or not token:
        print("ERROR: define HOSTINGER_INGEST_URL y HOSTINGER_INGEST_TOKEN.",
              file=sys.stderr)
        return 2

    try:
        res = _post(url, token, articles)
    except urllib.error.HTTPError as e:
        print(f"ERROR HTTP {e.code}: {e.read().decode('utf-8', 'replace')}",
              file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"ERROR de conexión: {e.reason}", file=sys.stderr)
        return 1

    print(f"OK: {res}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
