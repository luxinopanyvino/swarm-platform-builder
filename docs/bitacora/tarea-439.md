# Tarea #439 — T20.7 Revisor que no aprueba por defecto y definición del bloqueante de juicio

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-7-revisor-falla-cerrado`
- **PR:** la de esta rama → `develop` (`Closes #439`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC15 (y la definición que usa AC10) · ADR-0011 · épica E20 (#432)
- **Dependencias:** ninguna (T20.8, T20.11 y T20.15 dependen de esta)

### Dónde estaba el problema

`adapters/revisor.py` **fallaba abierto**: sin JSON válido conservaba `approval_score = 85` y
`coherent = True`; con error del LLM inventaba una revisión (75 con comentarios sobre Qdrant en la
primera vuelta, 90 «mejorado» en las siguientes). Un fallo del modelo se leía como aprobación.

### Qué se hizo y por qué

- `adapters/revisor.py`: el estado por defecto es `review_status = "not_verified"`. Solo pasa a
  `ok` si hay un JSON con `approval_score` numérico en 0–100 (los booleanos se rechazan). Si no:
  `coherent = False`, `feedback = []`, y se registra el motivo. Se eliminaron el 85 y la revisión
  simulada. Con `not_verified` no se abre la decisión humana «añadir fuente / continuar», porque
  no es una opinión sobre la coherencia.
- `approval_score` queda a `0` solo como valor de **enrutado** (para que el bucle vuelva al
  Redactor y cuente la vuelta); no es una puntuación del Revisor.
- `platform/explainability.py` (`decision_of`): en la traza una revisión no verificada registra
  `score = null` y `review_status`, no el 0 del enrutador.
- `platform/publication_gate/review.py` (nuevo): `judgment_blockers` / `review_approves` fijan la
  definición provisional de la Fase 1 — `approval_score < 80`, `coherent = false` o
  `review_status = not_verified`—. Será el insumo de `can_publish` (T20.11).
- `AgentState.review_status` añadido.
- **EDD (misma PR, GOVERNANCE §6):** caso nuevo `revisor-sin-veredicto` en `revisor-regressions`
  (falla a propósito: la calibración dice que no hay puntuación que calibrar). `revisor-golden` no cambia.

### Definition of Done

- [x] **AC15** — respuesta no interpretable o error del LLM → `not_verified`, bloqueante de juicio, sin 85 ni revisión inventada; una respuesta válida sigue funcionando.
- [x] Tests: `backend/tests/test_revisor_fail_closed.py` (13) en verde.
- [x] Gate EDD sin regresión (`replay`); la suite completa da los mismos 4 fallos que `develop`
  (`test_frontend_layers` ×2, `test_no_tracked_databases`, `test_la_spec_de_finetune_sigue_en_draft`), 1119 pasados.
- [ ] Efecto en el flujo (3 vueltas → `requires_human_review`): T20.8 (#440).

### Verificación

Mocks del LLM; no se probó con un modelo real. El gate corre en `replay`: mide las métricas, no al modelo.

### Fuera de alcance / notas

- **Cambio de comportamiento visible:** con un LLM caído o que no devuelve JSON, el Revisor ya no
  deja pasar el borrador; el bucle vuelve al Redactor hasta agotar las vueltas. Hasta T20.8 el
  flujo tras la 3.ª vuelta sigue avanzando; ahí se cierra.
- El umbral 80 está duplicado en `review.py` y en la plantilla del proyecto; unificarlo cuando la
  compuerta lea `template.yaml` (T20.4).
