# Tarea #382 — T13.1 Dataset y harness de benchmark de modelos base

## 2026-09-15 — Completada ✅ (verificación de trabajo previo)

- **Rama:** `docs/cerrar-t13-1-t13-2`
- **PR:** la de esta rama → `develop` (`Closes #382`)
- **Spec/ADR:** [SPEC-025](../specs/SPEC-025-model-benchmark-scientific-writing.md) (AC1, AC4) · ADR-0006
- **Dependencias:** ninguna

### Qué se hizo

La tarea se implementó el 2026-08-09 en el commit `d70c67f`, en local y antes de que
SPEC-025 saliera de `Draft`. Por eso `/sdd-sync` no creó su issue hasta el
2026-09-15. Esta entrada **no añade código**: verifica que lo que ya existe cumple la
tarea y la cierra por el flujo.

- `backend/evals/model_benchmark/dataset.py`: prompts fijos para los cuatro roles
  reales del pipeline (`sintesis_investigacion`, `redaccion_borrador`,
  `revision_estructurada`, `formateo_citas_apa`), con checks deterministas por tarea.
- `backend/evals/model_benchmark/run_benchmark.py`: CLI con `--models`, `--output` y
  `--ollama-exe`. Llama por el dispatcher de la plataforma (`app.platform.llm.call_llm`)
  y mide latencia, palabras por segundo y RAM/VRAM del modelo cargado vía `GET /api/ps`.
- `backend/tests/test_model_benchmark_smoke.py`: tests de humo sin red.

### Definition of Done

- [x] **AC1** (harness sobre un dataset fijo de las cuatro tareas, con métricas de
  calidad y cómputo por modelo y rol): el harness genera esas métricas. El informe que
  produjo se verifica en la tarea #383.
- [x] **AC4** (re-ejecutable, versionado, sin dependencias de pago): script versionado
  con `--models` para nuevos candidatos; solo necesita Ollama local.

### Verificación

- `python -m pytest tests/test_model_benchmark_smoke.py` (desde `backend/`) → 4 passed.
- Lectura de `dataset.py` y `run_benchmark.py`: cuatro roles, CLI y uso de `call_llm`.

### Fuera de alcance / notas

- No se ha vuelto a ejecutar el benchmark completo: necesita Ollama y varias horas.
  Repetirlo, sobre todo para el revisor, es parte de T13.3 (#384).
