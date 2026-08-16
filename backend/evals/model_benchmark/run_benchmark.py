"""Model benchmark runner — SPEC-025 / epic E13 (T13.1 / T13.2).

Runs every candidate model against the fixed task set in ``dataset.py`` and
writes a comparative markdown report to ``docs/reports/``.

Usage (from ``backend/``, with the venv active and Ollama + the candidate
models pulled locally):

    python -m evals.model_benchmark.run_benchmark \\
        --models llama3.2:1b,llama3.2:3b,mistral:7b,gemma2:2b,qwen2.5:3b \\
        --output ../docs/reports/model-benchmark-scientific-writing.md

Reuses the platform's own LLM dispatcher (``app.platform.llm.call_llm``) —
no separate HTTP client — so results reflect exactly how the pipeline calls
models in production (same retry/timeout semantics).

No paid/external service is used (SPEC-025 AC4): everything runs against the
local Ollama instance.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import subprocess
import time
from pathlib import Path
from typing import Any

import httpx

from evals.model_benchmark.dataset import BenchmarkTask, build_tasks

DEFAULT_MODELS = ["llama3.2:1b", "llama3.2:3b", "mistral:7b", "gemma2:2b", "qwen2.5:3b"]


async def _loaded_model_footprint(ollama_base_url: str, model: str) -> dict[str, Any]:
    """Best-effort read of RAM/VRAM currently used by `model` via GET /api/ps."""
    try:
        async with httpx.AsyncClient(base_url=ollama_base_url, timeout=10.0) as client:
            resp = await client.get("/api/ps")
            resp.raise_for_status()
            for entry in resp.json().get("models", []):
                if entry.get("name") == model or entry.get("model") == model:
                    return {
                        "ram_mb": round(entry.get("size", 0) / (1024 * 1024), 1),
                        "vram_mb": round(entry.get("size_vram", 0) / (1024 * 1024), 1),
                    }
    except Exception:
        pass
    return {"ram_mb": None, "vram_mb": None}


def _unload_model(ollama_exe: str, model: str) -> None:
    """Free RAM/VRAM before moving to the next candidate (important on low-RAM hosts)."""
    try:
        subprocess.run([ollama_exe, "stop", model], capture_output=True, timeout=30)
    except Exception:
        pass


async def run_task(model: str, task: BenchmarkTask, ollama_base_url: str) -> dict[str, Any]:
    from app.platform.llm import call_llm

    start = time.perf_counter()
    try:
        # keep_alive=15s (not the production 0): keeps the model resident just
        # long enough to read its footprint from /api/ps right after the call.
        text = await call_llm(
            task.prompt, model=model, timeout=task.timeout,
            num_ctx=task.num_ctx, keep_alive=15,
        )
        elapsed = time.perf_counter() - start
        footprint = await _loaded_model_footprint(ollama_base_url, model)
        scores = task.score_fn(text)
        words = len(text.split())
        return {
            "ok": True,
            "elapsed_s": round(elapsed, 2),
            "words": words,
            "words_per_s": round(words / elapsed, 2) if elapsed > 0 else None,
            "scores": scores,
            "avg_score": round(sum(scores.values()) / len(scores), 1) if scores else None,
            **footprint,
            "output_preview": text[:280].replace("\n", " "),
        }
    except Exception as exc:
        elapsed = time.perf_counter() - start
        return {
            "ok": False, "elapsed_s": round(elapsed, 2), "error": f"{type(exc).__name__}: {exc}",
            "words": 0, "words_per_s": None, "scores": {}, "avg_score": 0.0,
            "ram_mb": None, "vram_mb": None, "output_preview": "",
        }


async def run_all(models: list[str], ollama_base_url: str, ollama_exe: str) -> dict[str, dict[str, Any]]:
    tasks = build_tasks()
    results: dict[str, dict[str, Any]] = {}
    for model in models:
        print(f"\n=== {model} ===")
        results[model] = {}
        for task in tasks:
            print(f"  - {task.role}/{task.name} ...", end=" ", flush=True)
            res = await run_task(model, task, ollama_base_url)
            results[model][task.name] = res
            status = "ok" if res["ok"] else f"ERROR: {res.get('error')}"
            print(f"{status} ({res['elapsed_s']}s)")
        _unload_model(ollama_exe, model)
    return results


def render_report(results: dict[str, dict[str, Any]], models: list[str]) -> str:
    tasks = build_tasks()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    lines: list[str] = []
    lines.append("# Benchmark comparativo de modelos — redacción científica (SPEC-025)")
    lines.append("")
    lines.append(f"Generado automáticamente por `evals/model_benchmark/run_benchmark.py` el {now}.")
    lines.append("")
    lines.append(
        "Métricas: `avg_score` (calidad, checks deterministas 0-100 por tarea — ver "
        "`dataset.py`), `elapsed_s` (latencia), `words/s` (proxy de throughput), "
        "`ram_mb`/`vram_mb` (huella del modelo cargado vía `GET /api/ps` de Ollama)."
    )
    lines.append("")

    # Summary table: avg quality score and avg latency per model across all tasks
    lines.append("## Resumen por modelo")
    lines.append("")
    lines.append("| Modelo | Score calidad medio | Latencia media (s) | Palabras/s media | RAM/VRAM media (MB) | Errores |")
    lines.append("|---|---|---|---|---|---|")
    for model in models:
        per_task = results.get(model, {})
        scores = [r["avg_score"] for r in per_task.values() if r.get("avg_score") is not None]
        elapsed = [r["elapsed_s"] for r in per_task.values()]
        wps = [r["words_per_s"] for r in per_task.values() if r.get("words_per_s")]
        ram = [r["ram_mb"] for r in per_task.values() if r.get("ram_mb")]
        errors = sum(1 for r in per_task.values() if not r.get("ok"))
        avg_score = round(sum(scores) / len(scores), 1) if scores else "—"
        avg_elapsed = round(sum(elapsed) / len(elapsed), 1) if elapsed else "—"
        avg_wps = round(sum(wps) / len(wps), 1) if wps else "—"
        avg_ram = round(sum(ram) / len(ram), 0) if ram else "—"
        lines.append(f"| `{model}` | {avg_score} | {avg_elapsed} | {avg_wps} | {avg_ram} | {errors}/{len(tasks)} |")
    lines.append("")

    # Per-role detail
    for task in tasks:
        lines.append(f"## Rol: {task.role} ({task.name})")
        lines.append("")
        metric_names = sorted({k for r in results.values() for k in r.get(task.name, {}).get("scores", {})})
        header = ["Modelo", "avg_score", "elapsed_s", "words/s", "RAM/VRAM (MB)"] + metric_names
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "---|" * len(header))
        for model in models:
            r = results.get(model, {}).get(task.name, {})
            if not r.get("ok", False):
                row = [f"`{model}`", "ERROR", str(r.get("elapsed_s", "—")), "—", "—"] + ["—"] * len(metric_names)
            else:
                ram = r.get("ram_mb") or r.get("vram_mb") or "—"
                row = [f"`{model}`", str(r.get("avg_score")), str(r["elapsed_s"]), str(r.get("words_per_s")), str(ram)]
                row += [str(r["scores"].get(m, "—")) for m in metric_names]
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")

    lines.append("## Selección (AC2 — a completar por la comisión)")
    lines.append("")
    lines.append(
        "> Pendiente de revisión humana. Completar por agente, con la justificación "
        "explícita razonamiento vs. capacidad de cómputo (SPEC-025 AC2):"
    )
    lines.append("")
    lines.append("- **Investigador:** _TBD_")
    lines.append("- **Redactor:** _TBD_")
    lines.append("- **Revisor:** _TBD_")
    lines.append("- **Formateador:** _TBD_")
    lines.append("")

    return "\n".join(lines)


async def main_async(args: argparse.Namespace) -> None:
    from app.core.config import settings

    models = [m.strip() for m in args.models.split(",") if m.strip()]
    results = await run_all(models, settings.OLLAMA_BASE_URL, args.ollama_exe)
    report = render_report(results, models)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nInforme escrito en: {out_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=",".join(DEFAULT_MODELS), help="Lista separada por comas de modelos Ollama a comparar")
    parser.add_argument("--output", default="../docs/reports/model-benchmark-scientific-writing.md")
    parser.add_argument("--ollama-exe", default="ollama", help="Ruta al ejecutable de Ollama (para descargar el modelo entre comparaciones)")
    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
