"""Runner del harness EDD (SPEC-014 / T9.3 / AC3).

Ejecuta un **perfil de agente de la plataforma** sobre un dataset y produce un
informe de métricas con la procedencia completa: modelo, parámetros, versión y
hash del dataset, proveedor de LLM activo y modo de ejecución.

Uso (desde `backend/`):

    # Reproducible y sin servicios externos — lo que corre en la CI (T9.5)
    python -m evals.agent_behavior.runner --dataset redactor-smoke --mode replay

    # Contra el agente real, con el modelo y los parámetros de la plataforma
    python -m evals.agent_behavior.runner --dataset redactor-smoke --mode live

    # Guardar el informe
    python -m evals.agent_behavior.runner --dataset redactor-smoke --out evals/results
"""
from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from evals.agent_behavior import (
    judge as jueces, loader, metrics as metricas, providers, report,
)
from evals.agent_behavior.models import CaseResult, EvalCase, EvalReport, RunContext


def _git_sha() -> str:
    """Commit con el que se ejecutó. Sin él, comparar informes es adivinar."""
    try:
        salida = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return salida.stdout.strip() if salida.returncode == 0 else ""
    except Exception:
        return ""


def _contexto_del_agente(agent: str, mode: str) -> Dict[str, Any]:
    """Modelo y parámetros con los que corre el agente **en esta plataforma**.

    Se registran siempre, también en `replay`: son lo que dice a qué
    configuración corresponde el número, y sin ellos dos informes con la misma
    puntuación pueden venir de modelos distintos.
    """
    try:
        from app.core.config import settings
        from app.platform.llm import resolve_agent_model

        return {
            "model": resolve_agent_model(agent),
            "llm_provider": settings.LLM_PROVIDER,
        }
    except Exception as error:  # la plataforma puede no estar configurada
        return {"model": f"(no resuelto: {error.__class__.__name__})", "llm_provider": ""}


async def evaluate_case(
    caso: EvalCase,
    provider: providers.Provider,
    seleccionadas: Optional[List[str]] = None,
    judge: Optional[jueces.Judge] = None,
) -> CaseResult:
    """Ejecuta un caso y le pasa las métricas que le aplican."""
    resultado = CaseResult(case_id=caso.id, agent=caso.agent)
    try:
        salida, uso = await provider.run(caso)
    except Exception as error:
        resultado.error = f"{error.__class__.__name__}: {error}"
        return resultado

    resultado.output = salida
    resultado.tokens_in = int(uso.get("tokens_in") or 0)
    resultado.tokens_out = int(uso.get("tokens_out") or 0)
    resultado.latency_ms = float(uso.get("latency_ms") or 0.0)
    resultado.decision = uso.get("decision")

    # El juez se pide **aquí**, donde se sabe el modo, y no dentro de la métrica:
    # así `coherence` sigue siendo una función pura y en `replay` no se llama a
    # ningún modelo. Un juez que falla no tumba el caso — la métrica se saltará
    # con motivo, que es más honesto que puntuar sin haber mirado.
    if judge is not None and jueces.needs_judgement(caso):
        try:
            resultado.judgement = await judge.assess(caso, resultado)
        except Exception as error:
            resultado.judgement = None
            print(
                f"[aviso] el juez falló en el caso '{caso.id}': "
                f"{error.__class__.__name__}: {error}",
                file=sys.stderr,
            )

    for metrica in metricas.all_metrics():
        if seleccionadas and metrica.name not in seleccionadas:
            continue
        if not metrica.applies_to(caso):
            resultado.metrics.append(
                metricas.skipped(metrica.name, "no aplica a este caso")
            )
            continue
        try:
            resultado.metrics.append(metrica.run(caso, resultado))
        except Exception as error:
            # Una métrica rota no puede tumbar la evaluación entera, pero
            # tampoco pasar por buena: se marca como fallada con su motivo.
            resultado.metrics.append(metricas.MetricResult(
                name=metrica.name, score=0.0, passed=False,
                detail=f"la métrica falló: {error.__class__.__name__}: {error}",
            ))
    return resultado


async def run(
    dataset_id: str,
    *,
    mode: str = providers.MODO_REPLAY,
    agent: Optional[str] = None,
    only_metrics: Optional[List[str]] = None,
) -> EvalReport:
    """Evalúa `dataset_id` y devuelve el informe."""
    dataset = loader.load_by_id(dataset_id)

    agentes = [agent] if agent else list(dataset.agents())
    if agent and not dataset.for_agent(agent):
        raise SystemExit(
            f"El dataset '{dataset_id}' no tiene casos para '{agent}'. "
            f"Tiene: {', '.join(dataset.agents())}"
        )

    # Un informe describe un agente: mezclar dos en el mismo hace incomparables
    # sus medias. Con varios agentes se evalúa el primero y se avisa.
    objetivo = agentes[0]
    if len(agentes) > 1:
        print(
            f"[aviso] el dataset cubre {len(agentes)} agentes ({', '.join(agentes)}); "
            f"se evalúa '{objetivo}'. Usa --agent para elegir otro.",
            file=sys.stderr,
        )

    contexto_agente = _contexto_del_agente(objetivo, mode)
    contexto = RunContext(
        provider_mode=mode,
        agent=objetivo,
        model=contexto_agente["model"],
        params={},
        dataset_id=dataset.id,
        dataset_version=dataset.version,
        dataset_sha256=dataset.sha256,
        dataset_provenance=dataset.provenance,
        llm_provider=contexto_agente["llm_provider"],
        git_sha=_git_sha(),
    )

    provider = providers.build(mode, objetivo)
    judge = jueces.build(mode)
    informe = EvalReport(context=contexto)
    for caso in dataset.for_agent(objetivo):
        informe.cases.append(await evaluate_case(caso, provider, only_metrics, judge))
    return informe


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dataset", required=True, help=f"uno de: {', '.join(loader.available())}")
    parser.add_argument(
        "--mode", default=providers.MODO_REPLAY,
        choices=[providers.MODO_REPLAY, providers.MODO_LIVE],
        help="replay reproduce salidas grabadas (reproducible, sin servicios externos); "
             "live llama al agente real de la plataforma",
    )
    parser.add_argument("--agent", default=None, help="agente a evaluar (por defecto, el del dataset)")
    parser.add_argument("--metric", action="append", default=None, help="limitar a estas métricas")
    parser.add_argument("--out", default=None, help="directorio donde guardar el informe")
    args = parser.parse_args(argv)

    informe = asyncio.run(run(
        args.dataset, mode=args.mode, agent=args.agent, only_metrics=args.metric,
    ))

    print(report.to_markdown(informe))
    if args.out:
        rutas = report.save(informe, Path(args.out))
        print("\nInforme guardado en:")
        for ruta in rutas:
            print(f"  {ruta}")

    return 0 if informe.passed else 1


if __name__ == "__main__":
    sys.exit(main())
