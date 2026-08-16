"""Fixed benchmark dataset: one task per real agent role.

Every prompt mirrors the *actual* production template of its role (see
``backend/app/modules/agents/adapters/{redactor,revisor,formateador}.py`` and
``investigador.py``) with fixed, representative inputs, so every candidate
model answers the exact same question and results are comparable.

Deliberately small and self-contained (no RAG/network dependency) so the
harness runs anywhere Ollama is reachable, per SPEC-025 AC4 (re-runnable,
no paid/external services).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class BenchmarkTask:
    role: str                      # matches the pipeline agent name
    name: str                      # short id for the report
    prompt: str
    timeout: float
    num_ctx: int
    # Deterministic checker: (output_text) -> dict of metric_name -> 0..100 score
    score_fn: Callable[[str], dict]
    expected_words: int | None = field(default=None)


# ---------------------------------------------------------------------------
# Fixed fixtures (shared across tasks so results are directly comparable)
# ---------------------------------------------------------------------------

_TITLE = "Programación por currículo en aprendizaje por refuerzo para robótica de manipulación"
_KEYWORDS = ["curriculum learning", "aprendizaje por refuerzo", "robótica", "manipulación"]

_SOURCES = [
    {
        "title": "Curriculum Learning for Reinforcement Learning Domains: A Framework and Survey",
        "authors": "Narvekar et al.",
        "year": "2020",
        "snippet": (
            "Propone una taxonomía de métodos de curriculum learning para RL, "
            "clasificándolos según cómo se genera, ordena y transfiere la secuencia de tareas."
        ),
    },
    {
        "title": "Automatic Curriculum Learning For Deep RL: A Short Survey",
        "authors": "Portelas et al.",
        "year": "2020",
        "snippet": (
            "Revisa métodos de generación automática de curricula basados en progreso de "
            "aprendizaje, mostrando mejoras de muestra-eficiencia frente a entrenamiento uniforme."
        ),
    },
    {
        "title": "Solving Rubik's Cube with a Robot Hand",
        "authors": "OpenAI et al.",
        "year": "2019",
        "snippet": (
            "Usa domain randomization progresivo (una forma de curriculum implícito) para "
            "transferir una política entrenada en simulación a una mano robótica física."
        ),
    },
]

_RESEARCH_DATA = "\n\n".join(
    f"- {s['title']} ({s['authors']}, {s['year']}): {s['snippet']}" for s in _SOURCES
)

# A deliberately imperfect draft: thin methodology, no explicit numeric
# results — good stress test for the Revisor's calibration.
_DRAFT_FOR_REVIEW = """\
# Programación por currículo en aprendizaje por refuerzo para robótica de manipulación

## Resumen
Este trabajo explora el uso de curriculum learning para acelerar el entrenamiento de
políticas de aprendizaje por refuerzo en tareas de manipulación robótica.

## Introducción
El aprendizaje por refuerzo ha mostrado resultados prometedores en robótica, pero el
entrenamiento directo sobre tareas complejas suele ser lento e inestable. El curriculum
learning propone ordenar las tareas de más simples a más difíciles.

## Metodología
Se entrenó un agente con una secuencia de tareas de dificultad creciente.

## Resultados y Discusión
El agente entrenado con currículo aprendió más rápido que la línea base.
"""

# A draft with an informal reference list to reformat (Formateador task).
_DRAFT_FOR_FORMATTING = """\
# Programación por currículo en aprendizaje por refuerzo para robótica de manipulación

## Introducción
Trabajos previos (Narvekar 2020, Portelas 2020 y OpenAI 2019) muestran que ordenar las
tareas de entrenamiento por dificultad acelera la convergencia de políticas de RL en
robótica de manipulación.

## Referencias
1. Narvekar S. et al. Curriculum Learning for Reinforcement Learning Domains. 2020.
2. Portelas R. et al. Automatic Curriculum Learning For Deep RL: A Short Survey. 2020.
3. OpenAI et al. Solving Rubik's Cube with a Robot Hand. 2019.
"""


# ---------------------------------------------------------------------------
# Deterministic scorers
# ---------------------------------------------------------------------------

def _coverage_score(text: str, required_terms: list[str]) -> float:
    low = text.lower()
    hits = sum(1 for t in required_terms if t.lower() in low)
    return round(100.0 * hits / len(required_terms), 1) if required_terms else 100.0


def _section_presence_score(text: str, headers: list[str]) -> float:
    low = text.lower()
    hits = sum(1 for h in headers if h.lower() in low)
    return round(100.0 * hits / len(headers), 1) if headers else 100.0


def _word_count_score(text: str, target: int, tolerance: float = 0.35) -> float:
    actual = len(text.split())
    if target <= 0:
        return 100.0
    ratio = actual / target
    if abs(ratio - 1) <= tolerance:
        return 100.0
    # linear falloff beyond tolerance, floored at 0
    overshoot = abs(ratio - 1) - tolerance
    return round(max(0.0, 100.0 - overshoot * 150.0), 1)


def score_investigador(text: str) -> dict:
    terms = ["Narvekar", "Portelas", "OpenAI", "2020", "2019"]
    return {
        "cobertura_fuentes": _coverage_score(text, terms),
        "longitud_adecuada": _word_count_score(text, target=180, tolerance=0.6),
    }


def score_redactor(text: str) -> dict:
    headers = ["resumen", "abstract", "introduc", "metodolog", "resultado"]
    return {
        "secciones_presentes": _section_presence_score(text, headers),
        "longitud_adecuada": _word_count_score(text, target=500, tolerance=0.5),
        "cita_fuentes": _coverage_score(text, ["Narvekar", "Portelas"]),
    }


def score_revisor(text: str) -> dict:
    import json
    import re

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return {"json_valido": 0.0, "esquema_correcto": 0.0}
    try:
        data = json.loads(m.group(0))
    except Exception:
        return {"json_valido": 0.0, "esquema_correcto": 0.0}

    schema_hits = 0
    total = 3
    score = data.get("approval_score")
    if isinstance(score, (int, float)) and 0 <= score <= 100:
        schema_hits += 1
    if isinstance(data.get("coherent"), bool):
        schema_hits += 1
    fb = data.get("feedback")
    if isinstance(fb, list) and all(isinstance(x, str) for x in fb):
        schema_hits += 1

    return {
        "json_valido": 100.0,
        "esquema_correcto": round(100.0 * schema_hits / total, 1),
    }


def score_formateador(text: str) -> dict:
    import re

    # APA in-text citation pattern: (Author, Year)
    apa_intext = len(re.findall(r"\([A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑáéíóúñ\.\s]*,\s*\d{4}\)", text))
    body_preserved = _word_count_score(text, target=len(_DRAFT_FOR_FORMATTING.split()), tolerance=0.5)
    return {
        "citas_estilo_apa": min(100.0, apa_intext * 34.0),
        "cuerpo_preservado": body_preserved,
    }


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

def build_tasks() -> list[BenchmarkTask]:
    investigador_prompt = (
        "Eres un agente de investigación científica. Sintetiza en un único texto "
        "estructurado (español, ~180 palabras) las siguientes fuentes sobre "
        f"'{_TITLE}', citando autor y año explícitamente para cada idea:\n\n"
        f"{_RESEARCH_DATA}\n\n"
        "Contexto de investigación sintetizado:"
    )

    redactor_prompt = (
        "Eres un escritor científico experto. Redacta un borrador de artículo científico en Markdown.\n"
        f"\nTítulo: {_TITLE}\n"
        f"Palabras clave: {', '.join(_KEYWORDS)}\n"
        "### Contexto de investigación (incorpora estos datos y cita apropiadamente):\n"
        f"{_RESEARCH_DATA}\n\n"
        "Escribe un manuscrito científico estructurado que contenga:\n"
        "- Resumen (Abstract)\n- Introducción\n- Metodología\n- Resultados y Discusión Preliminares\n\n"
        "Redacta el borrador en español, con lenguaje académico y profesional. "
        "Longitud objetivo: 500 palabras."
    )

    revisor_prompt = (
        "Identity: You are a Senior Software Engineer Expert in LLMOps and multi-agent systems.\n"
        "Exact technology stack: Python, FastAPI, LangGraph (v2), Qdrant and a local inference engine (like Ollama/vLLM).\n\n"
        "You are acting as a peer reviewer for a scientific journal. Evaluate the following draft.\n\n"
        f"Draft Content:\n{_DRAFT_FOR_REVIEW}\n\n"
        "Evaluate the draft for scientific rigor, clarity, structure, academic style, and especially "
        "COHERENCE (does it stay on-topic, are the arguments internally consistent, do the sections "
        "connect logically and is it grounded rather than vague/hallucinated?).\n"
        "You must return your evaluation in JSON format. Do not write markdown blocks before the JSON.\n"
        "The JSON MUST match this schema:\n"
        '{\n  "approval_score": <int between 0 and 100>,\n'
        '  "coherent": <true or false>,\n'
        '  "feedback": [<list of string review comments>]\n}\n\n'
        "JSON output:"
    )

    formateador_prompt = (
        "Eres un agente de maquetación científica. Reescribe ÚNICAMENTE las citas en texto y "
        "la sección de Referencias del siguiente artículo al estilo APA (7ª edición), sin alterar "
        "el resto del contenido:\n\n"
        f"{_DRAFT_FOR_FORMATTING}\n\n"
        "Artículo con citas y referencias en formato APA:"
    )

    return [
        BenchmarkTask(
            role="investigador", name="sintesis_investigacion", prompt=investigador_prompt,
            timeout=180.0, num_ctx=8192, score_fn=score_investigador, expected_words=180,
        ),
        BenchmarkTask(
            role="redactor", name="redaccion_borrador", prompt=redactor_prompt,
            timeout=600.0, num_ctx=4096, score_fn=score_redactor, expected_words=500,
        ),
        BenchmarkTask(
            role="revisor", name="revision_estructurada", prompt=revisor_prompt,
            timeout=120.0, num_ctx=4096, score_fn=score_revisor, expected_words=None,
        ),
        BenchmarkTask(
            role="formateador", name="formateo_citas_apa", prompt=formateador_prompt,
            timeout=180.0, num_ctx=4096, score_fn=score_formateador, expected_words=None,
        ),
    ]
