# Tarea #437 — T20.5 Redactor: separar Resultados y Discusión en el prompt

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-5-redactor-resultados-discusion`
- **PR:** la de esta rama → `develop` (`Closes #437`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC11 · épica E20 (#432)
- **Dependencias:** ninguna (T20.4 usará la estructura IMRaD que esto habilita)

### Dónde estaba el problema

`adapters/redactor.py` pedía «Resultados y Discusión Preliminares» como una sola sección (y el
reparto de palabras también). V03 (IMRaD) exige Resultados y Discusión separadas, y el criterio
de T20.4 fallaría siempre con un texto generado así.

### Qué se hizo y por qué

- Plantillas por defecto ES/EN: secciones `Resultados` y `Discusión` / `Results` y `Discussion`,
  con la instrucción explícita de no interpretar en Resultados.
- Reparto de palabras por sección: Resultados 25 % y Discusión 15 % (antes 40 % juntas; el total no cambia).
- Prompts de ampliación ES/EN y el perfil `projects/alejandria-magazine/agents/redactor.agent.md`
  nombran las dos secciones.
- **EDD (misma PR, GOVERNANCE §6):** `redactor-golden.jsonl` se actualiza —salida grabada con
  `## Resultados` y `## Discusión`, y `required_sections` con las cinco secciones.
- No se toca `evals/model_benchmark/dataset.py`: es otro harness (compara modelos) con su propio prompt.

### Definition of Done

- [x] **AC11 (parte del Redactor)** — el prompt produce las dos secciones separadas.
- [x] Tests: `backend/tests/test_redactor_imrad_sections.py` (2) en verde.
- [x] Gate EDD: `python -m evals.agent_behavior.gate` → ninguna métrica por debajo de su umbral
  (`redactor` coherence 88, format_compliance 100, sin regresión).
- [ ] El validador V03 sobre el texto final: pendiente (T20.4, #436).

### Verificación

Gate EDD en modo `replay`: **mide las métricas, no al modelo** (los golden son `handwritten`). No se
ejecutó el Redactor contra un LLM real, así que no está comprobado que un modelo respete la
separación; conviene mirarlo en una ejecución en vivo.

### Fuera de alcance / notas

- Hay un fallo de consola en Windows al imprimir el informe del gate (emoji, cp1252); se evita con
  `PYTHONIOENCODING=utf-8`. No se tocó.
