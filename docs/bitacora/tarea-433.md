# Tarea #433 — T20.1 Detector de marcadores de posición en el texto final

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-1-detector-marcadores`
- **PR:** la de esta rama → `develop` (`Closes #433`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC1 · épica E20 (#432) · ADR-0011
- **Dependencias:** ninguna

### Dónde estaba el problema

Nada comprobaba el texto final: un manuscrito con `(Author, Year)`, `[?]` o `TODO` podía
llegar a «Publicado» (matriz de implementación, criterio V01 ausente).

### Qué se hizo y por qué

Primer ladrillo de la compuerta, en el módulo nuevo `backend/app/platform/publication_gate/`
(genérico, no nombra agentes):

- `types.py`: `CriterionStatus` (`passed`, `failed`, `not_verified`, `not_implemented`),
  `CriterionResult` y `BLOCKING_STATUSES` (solo `failed` y `not_verified` bloquean, AC5).
- `placeholders.py`: `check_placeholders(text, markers)` — función pura, sin LLM. Lista cerrada
  de AC1; devuelve cada hallazgo con patrón, `offset`, línea y columna. Ignora bloques de código
  y código en línea (sustituyéndolos por espacios para conservar las posiciones).
- Decisión de detalle: `TODO`/`TBD`/`XXX` solo cuentan **enteros y en mayúsculas**, porque «todo
  el mundo» es español corriente y daría falsos positivos; los marcadores con corchetes o
  paréntesis ignoran mayúsculas.
- La lista es un parámetro: queda sin conectar a `template.yaml` (`gate.placeholders`) a
  propósito, porque la configuración y su validación al cargar son T20.4 (#436).

### Definition of Done

- [x] **AC1** — patrones bloqueantes con nombre y posición; código ignorado.
- [x] Tests: `backend/tests/test_gate_placeholders.py` (20 casos) en verde.
- [ ] Conexión al Publicador y a la configuración del proyecto: pendiente (T20.4).

### Verificación

`python -m pytest tests/test_gate_placeholders.py` → 20 passed. No se ejecutó el pipeline: el
detector todavía no está enganchado a ningún agente.

### Fuera de alcance / notas

- Sin cambios de migración, API ni frontend.
