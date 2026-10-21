# Tarea #468 — Evidencia por criterio y acciones sugeridas en el informe de la compuerta

## 2026-10-22 — Éxito ✅

- **Rama:** `feat/compuerta-explicacion-criterios`
- **PR:** la de esta rama → `develop` (`Closes #468`)
- **Origen:** seguimiento de SPEC-032 / E20 (#432). El panel solo decía «superado» o «no supera» y no explicaba qué se había comprobado ni
  qué hacer; la persona que revisa el borrador no sabía cómo avanzar.

### Qué se hizo y dónde

- **Módulo nuevo `backend/app/platform/publication_gate/explain.py`.** Por cada criterio emite, solo con códigos y datos (el texto lo pone el
  frontend, como ya hace con los errores de la API):
  - `summary`: qué se comprobó. En referencias, total y cuántas están bien, y —si el criterio supera— la lista (título, DOI, año, revista;
    tope de 50). En marcadores, cuántos hay; en la estructura, las secciones comprobadas o los problemas hallados.
  - `actions`: qué se puede hacer, solo si el criterio bloquea. `provide_doi` (con las referencias afectadas), `rerun_agent` (con el agente
    responsable de `gate.responsible`) y `edit_text`.
- **`gate.py`:** `GateReport.explanations` se calcula en `evaluate_gate` y `as_dict()` lo añade a cada criterio junto a `responsible_agent`.
  Es aditivo: los informes ya guardados no lo traen y el frontend debe tolerarlo (lo hace la tarea #469).
- **Tests** (`backend/tests/test_gate_explain.py`, 7 casos): criterio superado con evidencia y sin acciones; referencias que fallan fuera de la
  lista de buenas; orden de las acciones; sin agente responsable solo se propone editar; no verificado también propone; tope de evidencia.

### Definition of Done

- [x] Tests nuevos y los del módulo de la compuerta en verde.
- [x] Suite completa: 1400 pasados; 2 fallos que ya tenía `develop` (`test_la_spec_de_finetune_sigue_en_draft` de SPEC-031 y
  `test_no_tracked_databases` por un bloqueo de archivo de Windows). `test_tracing.py` no se pudo ejecutar localmente (falta `opentelemetry`
  en este entorno); corre en la CI.
- [ ] La CI de esta PR es la comprobación en Linux.

### Fuera de alcance / notas

- No cambia ningún veredicto de la compuerta ni la regla de decisión: solo añade información al informe.
- La reejecución concreta (a qué agente, con qué instrucción) la dispara el frontend con los endpoints que ya existen; esta tarea solo la sugiere.
