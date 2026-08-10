# Model benchmark — SPEC-025 / épica E13

Harness para comparar **modelos foundation open-source** (vía Ollama) en las
cuatro tareas reales del pipeline editorial: investigador, redactor, revisor,
formateador. Ver [SPEC-025](../../../docs/specs/SPEC-025-model-benchmark-scientific-writing.md).

**No confundir** con los evals de comportamiento de agentes (EDD, ADR-0006 /
SPEC-014, `T9.3`): ese harness evalúa agentes *ya configurados* en
producción; este compara modelos *antes* de configurarlos.

## Uso

Requisitos: Ollama corriendo en local con los modelos candidatos ya
descargados (`ollama pull <modelo>`).

```bash
cd backend
.venv/Scripts/python -m evals.model_benchmark.run_benchmark \
  --models llama3.2:1b,llama3.2:3b,mistral:7b,gemma2:2b,qwen2.5:3b \
  --output ../docs/reports/model-benchmark-scientific-writing.md
```

Cada modelo se ejecuta secuencialmente contra las 4 tareas fijas
(`dataset.py`) y se descarga de RAM/VRAM (`ollama stop`) antes de pasar al
siguiente — importante en hosts con RAM limitada. El informe se escribe en
Markdown con:

- **Resumen por modelo**: score de calidad medio, latencia media, palabras/s,
  RAM/VRAM media, tasa de errores.
- **Detalle por rol**: una tabla por agente con las métricas deterministas
  específicas de esa tarea (cobertura de fuentes, secciones presentes,
  validez de JSON, formato de citas APA, etc. — ver `dataset.py`).
- **Sección "Selección"**: a completar a mano por la comisión (AC2 de
  SPEC-025) con la justificación razonamiento vs. cómputo por agente.

## Métricas

Todas las métricas de calidad son **deterministas** (regex/heurísticas, sin
LLM-as-judge) para mantener el harness reproducible y barato de correr en
hardware modesto. `words/s` es una aproximación de throughput (no un conteo
real de tokens — evita depender de un tokenizador por modelo). RAM/VRAM se
lee de `GET /api/ps` de Ollama justo después de cada llamada.

## Tests

`backend/tests/test_model_benchmark_smoke.py` — mockea `call_llm`, no
requiere Ollama ni red; valida el cableado del harness (dataset → runner →
informe), no la calidad real de ningún modelo.
