# Tarea #480 — ADR-0012 de fine-tune local y retirada del test de SPEC-031 (DEC-8)

## 2026-10-22 — Éxito ✅

- **Rama:** `docs/adr-0012-finetune-local`
- **PR:** la de esta rama → `develop` (`Closes #480`)
- **Origen:** DEC-8. SPEC-031 salió de `Draft` a `Ready` (solo fase de decisión) y `test_la_spec_de_finetune_sigue_en_draft` fallaba en `develop`
  desde antes de E20: exigía que, si la spec salía de `Draft`, hubiera ADR delante y se borrara el test «a conciencia».

### Qué se hizo y dónde

- **`docs/adr/0012-local-finetune-format-learning.md` (Propuesto):** fija lo ya decidido en las *Clarifications* de SPEC-031 (sin datos de usuario en
  entrenamientos, un modelo por proyecto, lugar en la cascada de modelo, reversibilidad por adaptador, sin saltarse dispatcher/aislamiento/retención,
  criterio de adopción con golden `recorded` y revisión humana) y deja **abierto lo que debe medir el spike T19.1** (dónde se entrena, base y técnica).
  No inventa cifras: el spike no se ha hecho.
- **`docs/adr/README.md`:** entrada 0012. **SPEC-031:** su campo «ADR relacionado» apunta al ADR.
- **`backend/tests/test_spec_plan_coherence.py`:** se elimina el test (15 líneas). La salvaguarda que protegía —no implementar antes del ADR— queda en el
  propio ADR y en la spec (no se escribe código de entrenamiento en `backend/app` hasta aceptarlo).
- **`spec-032-decisiones-pendientes.md`:** DEC-8 resuelta.

### Definition of Done

- [x] `python scripts/validate_specs.py` en verde; `test_spec_plan_coherence.py` en verde (20).
- [ ] El ADR pasa a `Aceptado` cuando el spike T19.1 confirme la viabilidad (fuera de esta tarea).
- [ ] La CI de esta PR es la comprobación en Linux.
