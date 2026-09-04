"""Serialización del informe (SPEC-014 / T9.3 / AC3).

Dos formatos y para dos lectores distintos: JSON para que el gate de T9.5 compare
números sin parsear prosa, y markdown para que una persona entienda en diez
segundos qué salió mal y por qué.

El JSON se escribe con las claves ordenadas y sin el instante de generación
dentro de la comparación: dos ejecuciones idénticas en modo `replay` producen
ficheros idénticos, y eso es lo que hace que «ha cambiado el informe» signifique
«ha cambiado el comportamiento» y no «lo he vuelto a ejecutar».
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

from evals.agent_behavior.models import EvalReport


def to_json(informe: EvalReport, *, include_timestamp: bool = True) -> str:
    return json.dumps(
        informe.to_dict(include_timestamp=include_timestamp),
        ensure_ascii=False, indent=2, sort_keys=True,
    )


def fingerprint(informe: EvalReport) -> str:
    """El informe sin lo que cambia por el mero hecho de repetirlo."""
    return to_json(informe, include_timestamp=False)


def to_markdown(informe: EvalReport) -> str:
    contexto = informe.context
    lineas: List[str] = [
        f"# EDD — {contexto.agent} · {contexto.dataset_id}@{contexto.dataset_version}",
        "",
    ]

    if contexto.provider_mode == "replay":
        lineas += [
            "> **Modo `replay`.** Se reproducen salidas grabadas: esto evalúa las",
            "> métricas y el harness, **no al modelo**. Para medir el comportamiento",
            "> real, `--mode live`.",
            "",
        ]

    lineas += [
        "| | |",
        "|---|---|",
        f"| Agente | `{contexto.agent}` |",
        f"| Modelo | `{contexto.model}` |",
        f"| Proveedor | `{contexto.llm_provider or '—'}` |",
        f"| Modo | `{contexto.provider_mode}` |",
        f"| Dataset | `{contexto.dataset_id}` v`{contexto.dataset_version}` |",
        f"| Hash del dataset | `{contexto.dataset_sha256[:16]}…` |",
        f"| Commit | `{contexto.git_sha or '—'}` |",
        f"| Generado | {informe.generated_at} |",
        "",
        "## Resultado",
        "",
    ]

    totales = informe.totals()
    veredicto = "✅ pasa" if informe.passed else "❌ falla"
    lineas += [
        f"{veredicto} — {totales['passed']}/{totales['cases']} caso(s); "
        f"{totales['tokens_in']} tokens de entrada, {totales['tokens_out']} de salida.",
        "",
    ]

    puntuaciones = informe.scores()
    if puntuaciones:
        lineas += ["| Métrica | Media |", "|---|---:|"]
        lineas += [f"| `{nombre}` | {valor} |" for nombre, valor in puntuaciones.items()]
        lineas.append("")

    lineas += ["## Casos", ""]
    for caso in informe.cases:
        marca = "✅" if caso.passed else "❌"
        lineas.append(f"### {marca} `{caso.case_id}`")
        if caso.error:
            lineas += ["", f"No se pudo ejecutar: {caso.error}", ""]
            continue
        lineas += ["", "| Métrica | Puntuación | Detalle |", "|---|---:|---|"]
        for metrica in caso.metrics:
            if metrica.skipped_reason:
                lineas.append(f"| `{metrica.name}` | — | saltada: {metrica.skipped_reason} |")
            else:
                icono = "✅" if metrica.passed else "❌"
                lineas.append(
                    f"| `{metrica.name}` | {icono} {metrica.score} | {metrica.detail} |"
                )
        lineas.append("")

    return "\n".join(lineas)


def save(informe: EvalReport, directorio: Path) -> List[Path]:
    """Guarda el informe en JSON y markdown. Devuelve las rutas escritas."""
    directorio.mkdir(parents=True, exist_ok=True)
    contexto = informe.context
    # El modo va en el nombre: un `replay` no debe poder confundirse con una
    # medición real ni mirando el listado del directorio.
    base = f"{contexto.dataset_id}--{contexto.agent}--{contexto.provider_mode}"
    rutas = []
    for sufijo, contenido in ((".json", to_json(informe)), (".md", to_markdown(informe))):
        ruta = directorio / f"{base}{sufijo}"
        ruta.write_text(contenido, encoding="utf-8")
        rutas.append(ruta)
    return rutas
