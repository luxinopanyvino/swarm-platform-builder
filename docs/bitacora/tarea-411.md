# Tarea #411 — VAL-004 El Flow Designer permite un orden lógico inválido

## 2026-10-21 — Completada ✅

- **Rama:** `fix/val-004-pipeline-order` (apilada sobre `fix/bug-001-self-loop`)
- **PR:** [#416](https://github.com/onpremialabs/swarm-platform-builder/pull/416) → `develop` (`Closes #411`)
- **Origen:** informe de pruebas funcionales; plan `plan_fix_alejandria_magazine.md`
- **Dependencias:** #410 (comparte la capa de validación). Mergear después de #415.

### Dónde estaba el problema

- **Nada validaba el orden.** `backend/app/routers/flows.py` y `POST /agents/{id}/run`
  (`backend/app/routers/agents.py`) aceptaban cualquier secuencia: un pipeline con
  Publicador antes de Redactor se guardaba y se ejecutaba.
- **El orden dibujado no era el ejecutado.** `flowStore.saveFlow` y
  `FlowDesignerPage.handleRun` construían `flow_sequence` con el orden de creación de
  los nodos (`nodes.map(...)`), ignorando las aristas, y el motor ejecuta
  `flow_sequence`. Validar aristas sin corregir esto habría validado algo que no se
  ejecuta.

### Qué se modificó y por qué

- **`backend/app/platform/flow_validation.py`:** reglas `cycle` (ciclos de cualquier
  longitud, sin marcar los nodos que solo cuelgan de uno), `orphan` y reglas de
  dependencia `missing_dependency` / `wrong_order`. «Antes» = orden de ejecución:
  topológico por aristas y, en los empates, orden del lienzo.
- **Reglas como datos:** `backend/projects/alejandria-magazine/template.yaml`
  (`graph.flow_rules`) y `backend/app/platform/projects/loader.py` (lectura y
  validación al cargar). Hoy: Publicador sin Redactor → error; sin Revisor/Formateador
  → aviso; agente suelto → aviso. El módulo no nombra agentes concretos.
- **`satisfied_by_existing_output`:** re-publicar un artículo que ya tiene cuerpo no
  exige Redactor en el flujo (es un uso legítimo que, si no, habría roto).
- **`routers/flows.py`:** valida con las reglas del proyecto y sirve `GET /flows/rules`.
  **`routers/agents.py`:** valida la secuencia antes de lanzar (no en reanudaciones).
  Ambos responden 422 con regla, nodos y aristas implicados.
- **`core/config.py`:** `FLOW_RULES_ENFORCE` (por defecto `true`). Con `false` las
  dependencias pasan a aviso, para desplegar sin bloquear flujos ya guardados. Los
  ciclos y autoconexiones bloquean siempre.
- **Frontend:** `flowValidation.js` reimplementa el algoritmo con las reglas pedidas a
  la API; `FlowDesignerPage.jsx` resalta nodos y aristas implicados, lista los mensajes,
  y deshabilita Ejecutar y bloquea Guardar si hay errores; `flowStore.js` y `handleRun`
  usan `effectiveSequence` (orden de aristas).

### Definition of Done

- [x] **AC1** pipeline inválido rechazado o advertido identificando conexiones:
  `tests/test_flow_rules.py`.
- [x] **AC2** el backend rechaza aunque se salte la UI, en guardado y en ejecución:
  `test_flow_rules.py` (API de flujos) y `tests/test_run_flow_rules.py`.
- [x] Regresión: los flujos que trae la siembra siguen guardándose; re-publicar
  funciona.

### Verificación

- Suite completa: mismos 4 fallos preexistentes que en `develop`.
- Paridad JS ↔ Python comprobada a mano en 6 casos (misma salida); no es un test
  automático.
- `npm run build` y `build:public` OK. **No** se probó en navegador.

### Fuera de alcance / notas

- Las reglas son una propuesta mía; el plan pedía definirlas con producto. Conviene
  ratificarlas.
- Duplicación deliberada del algoritmo en JS y Python; solo las reglas son una fuente
  única.
