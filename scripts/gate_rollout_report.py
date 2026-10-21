#!/usr/bin/env python3
"""Qué fracción de los manuscritos pasaría la compuerta, y por qué criterio no (DEC-4).

Con `PUBLICATION_GATE_ENFORCE=false` la compuerta registra y avisa sin bloquear. Este
script lee esos informes (el último de cada artículo) y responde a la pregunta que
decide cuándo activarla: ¿los bloqueantes son accionables y, de los manuscritos
reales, cuántos pasarían? Solo lee; no cambia nada.

Uso (desde `backend/`, con la base del entorno que se quiere medir):
    DATABASE_URL=… python ../scripts/gate_rollout_report.py [--days 14] [--min-articles 20] [--min-pass 0.8]

Sale con código 0 si hay muestra suficiente y pasa al menos `--min-pass`; con 1 si no.
Es una recomendación, no un interruptor: activar `gate_enforce` lo decide una persona.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter
from datetime import datetime, timedelta

BLOQUEANTES = {"failed", "not_verified"}


def resumir(informes: list[dict], *, min_articulos: int = 20, min_pasa: float = 0.8) -> dict:
    """Resumen de los últimos informes de cada artículo (`criteria` del informe guardado)."""
    total = len(informes)
    pasan = sum(1 for i in informes if i.get("passed"))
    fallan: Counter = Counter()
    estados: Counter = Counter()
    for i in informes:
        for c in i.get("criteria", []):
            if c.get("status") in BLOQUEANTES:
                fallan[c["criterion"]] += 1
                estados[(c["criterion"], c["status"])] += 1
    solo_uno = sum(
        1 for i in informes
        if not i.get("passed") and sum(1 for c in i.get("criteria", []) if c.get("status") in BLOQUEANTES) == 1
    )
    fraccion = pasan / total if total else 0.0
    return {
        "total": total, "pasan": pasan, "fraccion_pasa": fraccion,
        "bloquean_por": dict(fallan.most_common()), "detalle_estado": {f"{k[0]}:{k[1]}": v for k, v in estados.items()},
        "bloqueados_por_un_solo_criterio": solo_uno,
        "muestra_suficiente": total >= min_articulos,
        "listo_para_activar": total >= min_articulos and fraccion >= min_pasa,
        "min_articulos": min_articulos, "min_pasa": min_pasa,
    }


def informe(r: dict) -> str:
    lineas = [
        "Despliegue gradual de la compuerta (DEC-4)",
        f"  manuscritos con informe : {r['total']} (mínimo {r['min_articulos']} para decidir)",
        f"  pasarían la compuerta   : {r['pasan']}/{r['total']} ({r['fraccion_pasa']:.0%}, umbral {r['min_pasa']:.0%})",
        f"  bloqueados por un solo criterio (corrección acotada): {r['bloqueados_por_un_solo_criterio']}",
        "  bloquean por criterio:",
    ]
    lineas += [f"    {n:>4}× {c}" for c, n in r["bloquean_por"].items()] or ["    (ninguno)"]
    if not r["muestra_suficiente"]:
        lineas.append("RESULTADO: muestra insuficiente; seguir en modo aviso.")
    elif r["listo_para_activar"]:
        lineas.append("RESULTADO: se puede plantear activar `gate_enforce` (decisión de una persona).")
    else:
        lineas.append("RESULTADO: aún no; revisar los criterios que más bloquean antes de activar.")
    return "\n".join(lineas)


async def cargar(days: int) -> list[dict]:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models import PublicationGateReportModel

    desde = datetime.utcnow() - timedelta(days=days)
    async with AsyncSessionLocal() as s:
        filas = (await s.execute(
            select(PublicationGateReportModel)
            .where(PublicationGateReportModel.created_at >= desde)
            .order_by(PublicationGateReportModel.created_at)
        )).scalars().all()
    ultimo: dict = {}
    for f in filas:  # orden ascendente: el último de cada artículo pisa al anterior
        ultimo[f.article_id] = f.criteria or {}
    return list(ultimo.values())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--min-articles", type=int, default=20)
    ap.add_argument("--min-pass", type=float, default=0.8)
    a = ap.parse_args(argv)
    r = resumir(asyncio.run(cargar(a.days)), min_articulos=a.min_articles, min_pasa=a.min_pass)
    print(informe(r))
    return 0 if r["listo_para_activar"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
