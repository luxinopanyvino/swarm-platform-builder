"""Smoke test for the model benchmark harness (SPEC-025 / T13.1).

Mocks the LLM call so it runs in CI without Ollama or network access — this
only verifies the harness plumbing (dataset -> runner -> report), not real
model quality. Real comparisons are run manually/locally (SPEC-025 AC1/AC4).
"""
from unittest.mock import AsyncMock, patch

import pytest

from evals.model_benchmark import run_benchmark
from evals.model_benchmark.dataset import build_tasks

FAKE_RESPONSES = {
    "sintesis_investigacion": "Narvekar (2020) y Portelas (2020) muestran... OpenAI (2019) demuestra...",
    "redaccion_borrador": (
        "# Resumen\ntexto\n## Introducción\ntexto\n## Metodología\ntexto\n"
        "## Resultados\ntexto Narvekar Portelas " + ("palabra " * 480)
    ),
    "revision_estructurada": '{"approval_score": 82, "coherent": true, "feedback": ["ok"]}',
    "formateo_citas_apa": "(Narvekar, 2020) (Portelas, 2020) (OpenAI, 2019)\n\n## Referencias\n...",
}


def test_dataset_has_one_task_per_pipeline_role():
    tasks = build_tasks()
    roles = {t.role for t in tasks}
    assert roles == {"investigador", "redactor", "revisor", "formateador"}


@pytest.mark.asyncio
async def test_run_task_scores_and_times_a_fake_model():
    task = build_tasks()[0]  # investigador
    with patch("app.platform.llm.call_llm", new=AsyncMock(return_value=FAKE_RESPONSES[task.name])):
        with patch.object(run_benchmark, "_loaded_model_footprint", new=AsyncMock(return_value={"ram_mb": 512.0, "vram_mb": None})):
            result = await run_benchmark.run_task("fake-model:1b", task, "http://localhost:11434")

    assert result["ok"] is True
    assert result["avg_score"] > 0
    assert result["ram_mb"] == 512.0
    assert result["elapsed_s"] >= 0


@pytest.mark.asyncio
async def test_run_task_marks_failure_without_crashing():
    task = build_tasks()[0]
    with patch("app.platform.llm.call_llm", new=AsyncMock(side_effect=RuntimeError("boom"))):
        result = await run_benchmark.run_task("fake-model:1b", task, "http://localhost:11434")

    assert result["ok"] is False
    assert "boom" in result["error"]
    assert result["avg_score"] == 0.0


@pytest.mark.asyncio
async def test_run_all_and_report_end_to_end():
    async def fake_call_llm(prompt, *, model=None, timeout=None, num_ctx=None, keep_alive=None):
        for name, text in FAKE_RESPONSES.items():
            if name == "sintesis_investigacion" and "Sintetiza" in prompt:
                return text
            if name == "redaccion_borrador" and "escritor científico" in prompt:
                return text
            if name == "revision_estructurada" and "peer reviewer" in prompt:
                return text
            if name == "formateo_citas_apa" and "maquetación científica" in prompt:
                return text
        return "respuesta genérica"

    with patch("app.platform.llm.call_llm", new=AsyncMock(side_effect=fake_call_llm)):
        with patch.object(run_benchmark, "_loaded_model_footprint", new=AsyncMock(return_value={"ram_mb": 800.0, "vram_mb": None})):
            with patch.object(run_benchmark, "_unload_model", return_value=None):
                results = await run_benchmark.run_all(["fake-model:1b"], "http://localhost:11434", "ollama")

    assert set(results["fake-model:1b"].keys()) == {t.name for t in build_tasks()}
    report = run_benchmark.render_report(results, ["fake-model:1b"])
    assert "# Benchmark comparativo de modelos" in report
    assert "fake-model:1b" in report
    assert "## Selección (AC2" in report
