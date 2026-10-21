# Tarea #410 — BUG-001 Un agente puede conectarse consigo mismo en el Flow Designer

## 2026-10-21 — Completada ✅

- **Rama:** `fix/bug-001-self-loop`
- **PR:** [#415](https://github.com/onpremialabs/swarm-platform-builder/pull/415) → `develop` (`Closes #410`)
- **Origen:** informe de pruebas funcionales (Pantoja, Molina); plan `plan_fix_alejandria_magazine.md`
- **Dependencias:** ninguna. VAL-004 (#411) se apila sobre esta rama.

### Dónde estaba el problema

- `frontend/src/platform/pages/FlowDesignerPage.jsx`, `onConnect`: añadía la arista con
  `addEdge` sin mirar si `source === target`, y el lienzo no tenía `isValidConnection`,
  así que el puerto se ofrecía como destino válido al arrastrar sobre el propio nodo.
- `backend/app/routers/flows.py`: `create_flow` y `update_flow` guardaban `nodes` y
  `edges` tal cual llegaban. Cualquiera podía persistir una autoconexión por la API.

### Qué se modificó y por qué

- **`backend/app/platform/flow_validation.py` (nuevo):** validación del grafo con
  problemas estructurados (`FlowIssue`: regla, severidad, mensaje, nodos y aristas).
  Aquí solo la regla `self_loop`. El backend es la validación que manda, porque la del
  navegador se salta con un `PUT`.
- **`backend/app/routers/flows.py`:** `_reject_invalid` responde 422 con los problemas
  al crear o actualizar. En `PUT` valida también lo ya guardado si no llegan aristas
  nuevas, y lo rechazado no altera lo persistido.
- **`frontend/src/platform/flowValidation.js` (nuevo):** el mismo contrato en el cliente.
- **`FlowDesignerPage.jsx`:** `isValidConnection` rechaza en el arrastre, `onConnect`
  muestra «Un agente no puede conectarse consigo mismo», y guardar valida antes de
  llamar a la API (muestra el mensaje del 422 si el backend rechaza).
- **`frontend/src/platform/store/flowStore.js`:** `loadFlow` descarta las
  autoconexiones de flujos guardados antes del arreglo (saneamiento sin migración de BD).

### Definition of Done

- [x] **AC1** la autoconexión no se crea ni se puede persistir: `tests/test_flow_validation.py`
  (unitarias y de integración, incluida la API sin pasar por la UI).
- [x] **AC2** el resto del flujo sigue editable: test de flujo válido y de que un `PUT`
  rechazado no cambia lo guardado.

### Verificación

- `pytest` completo (sin `test_tracing.py`, falta `opentelemetry` en este entorno):
  4 fallos que ya existen en `develop` sin estos cambios (`test_frontend_layers` ×2,
  `test_no_tracked_databases`, `test_spec_plan_coherence`).
- `npm run build` OK. **No** se probó en navegador.

### Fuera de alcance / notas

- Los flujos ya guardados con autoconexión se limpian al abrirlos, pero siguen en BD
  hasta el siguiente guardado.
