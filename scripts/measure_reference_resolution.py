#!/usr/bin/env python3
"""Mide la tasa real de resolución de referencias contra Crossref/OpenAlex.

SPEC-032 / AC3 fija un objetivo: «sobre un conjunto de referencias reales con DOI,
se resuelve y pasa al menos el 90 %». Los tests de `backend/tests/` lo prueban con
registros simulados, que comprueban la lógica de coincidencia pero **no** si
Crossref y OpenAlex devuelven lo que el resolutor espera. Este script es la
medición con la red.

Mide tres cosas, por separado porque no son lo mismo:

* **referencias válidas con DOI** — el objetivo del 90 %;
* **las mismas sin DOI** — la búsqueda por título y autores (más frágil);
* **controles negativos** (inventadas o alteradas) — **ninguna** puede pasar: una
  falsa aceptación es el fallo grave, un falso rechazo solo es molesto.

Usa el resolutor del producto tal cual (misma puerta de salida, mismos umbrales,
`template.yaml` incluido), no una copia. Hace unas ~110 consultas; es educado con los
servicios: secuencial y con correo de contacto si se le da.

Uso (desde la raíz del repo):
    cd backend
    DEBUG=true SECRET_KEY=local-medicion python ../scripts/measure_reference_resolution.py \\
        --contact tu@correo.org [--json informe.json]

Sale con código 1 si no se alcanza el objetivo o si algún control negativo pasa.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

DATASET = REPO / "backend" / "evals" / "reference_resolution" / "references.jsonl"
OBJETIVO = 0.90


def cargar(ruta: Path = DATASET) -> list[dict]:
    filas = [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [f for f in filas if "kind" in f]


def resumir(resultados: list[dict]) -> dict:
    """Agrega por tipo. Función pura para poder probarla sin red."""
    def tasa(kind: str, esperado: str) -> tuple[int, int]:
        filas = [r for r in resultados if r["kind"] == kind]
        return sum(1 for r in filas if r["outcome"] == esperado), len(filas)

    ok_doi, n_doi = tasa("valid_with_doi", "passed")
    ok_sin, n_sin = tasa("valid_without_doi", "passed")
    negativos = [r for r in resultados if r["expect"] == "block"]
    falsas_aceptaciones = [r["id"] for r in negativos if r["outcome"] == "passed"]
    return {
        "con_doi": {"pasan": ok_doi, "total": n_doi, "tasa": ok_doi / n_doi if n_doi else 0.0},
        "sin_doi": {"pasan": ok_sin, "total": n_sin, "tasa": ok_sin / n_sin if n_sin else 0.0},
        "negativos": {"bloqueados": len(negativos) - len(falsas_aceptaciones), "total": len(negativos)},
        "falsas_aceptaciones": falsas_aceptaciones,
        "objetivo": OBJETIVO,
        "cumple_objetivo": bool(n_doi) and ok_doi / n_doi >= OBJETIVO and not falsas_aceptaciones,
    }


async def medir(filas: list[dict], contacto: str) -> list[dict]:
    from dataclasses import replace

    from app.modules.agents.domain import alejandria
    from app.platform.publication_gate.reference_resolver import (
        PositiveCache, check_reference_existence,
    )

    # La configuración del proyecto, no una inventada para la medición.
    config = alejandria.package().gate.references
    if contacto:
        config = replace(config, contact_email=contacto)
    cache = PositiveCache(config.cache_ttl_days)

    resultados = []
    for fila in filas:
        fuente = {k: fila.get(k, "") for k in ("title", "authors", "year", "journal", "doi")}
        criterio, enriquecidas = await check_reference_existence([fuente], config, cache=cache)
        evidencia = criterio.evidence[0] if criterio.evidence else {}
        resultados.append({
            "id": fila["id"], "kind": fila["kind"], "expect": fila["expect"],
            "outcome": criterio.status.value,
            "reason": evidencia.get("reason", ""),
            "doi_resuelto": enriquecidas[0].get("doi", "") if enriquecidas else "",
        })
        print(f"  {criterio.status.value:13} {fila['id']}"
              + (f" — {evidencia['reason']}" if evidencia else ""), flush=True)
    return resultados


def informe(resumen: dict, resultados: list[dict]) -> str:
    def pct(x: dict) -> str:
        return f"{x['pasan']}/{x['total']} ({100 * x['tasa']:.0f} %)"

    lineas = [
        "",
        "Resolución de referencias (SPEC-032 / AC3)",
        f"  válidas con DOI : {pct(resumen['con_doi'])}   objetivo ≥ {100 * resumen['objetivo']:.0f} %",
        f"  válidas sin DOI : {pct(resumen['sin_doi'])}   (búsqueda por título y autores; sin objetivo fijado)",
        f"  controles negativos bloqueados: {resumen['negativos']['bloqueados']}/{resumen['negativos']['total']}",
    ]
    if resumen["falsas_aceptaciones"]:
        lineas.append(f"  ⚠ FALSAS ACEPTACIONES: {', '.join(resumen['falsas_aceptaciones'])}")
    motivos = Counter(r["reason"][:70] for r in resultados
                      if r["expect"] == "pass" and r["outcome"] != "passed")
    if motivos:
        lineas.append("  motivos de las válidas que no pasan:")
        lineas += [f"    {n}× {m}" for m, n in motivos.most_common()]
    lineas.append("  RESULTADO: " + ("CUMPLE" if resumen["cumple_objetivo"] else "NO CUMPLE"))
    lineas.append(
        "\nLímite: el conjunto lo escribió una persona de memoria. Cada fallo de una referencia válida "
        "hay que revisarlo a mano antes de culpar al resolutor."
    )
    return "\n".join(lineas)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--contact", default="", help="correo para el User-Agent (polite pool de Crossref/OpenAlex)")
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--json", type=Path, help="guarda el detalle en este fichero")
    args = parser.parse_args(argv)

    filas = cargar(args.dataset)
    print(f"Consultando Crossref/OpenAlex para {len(filas)} referencias…")
    resultados = asyncio.run(medir(filas, args.contact))
    resumen = resumir(resultados)
    print(informe(resumen, resultados))
    if args.json:
        args.json.write_text(
            json.dumps({"resumen": resumen, "detalle": resultados}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return 0 if resumen["cumple_objetivo"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
