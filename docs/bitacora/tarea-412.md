# Tarea #412 — BUG-003 No se pueden eliminar conexiones del Flow Designer

## 2026-10-21 — Completada ✅ (verificación pendiente en navegador)

- **Rama:** `fix/bug-003-delete-connections` (apilada sobre `fix/val-004-pipeline-order`)
- **PR:** [#417](https://github.com/onpremialabs/swarm-platform-builder/pull/417) → `develop` (`Closes #412`)
- **Origen:** informe de pruebas funcionales; plan `plan_fix_alejandria_magazine.md`
- **Dependencias:** #411 (al eliminar una conexión se revalida el grafo). Mergear después de #416.

### Dónde estaba el problema

En `frontend/src/platform/pages/FlowDesignerPage.jsx`:

- `deleteKeyCode="Delete"` sustituía el valor por defecto de React Flow (`Backspace`).
  En muchos portátiles la única tecla de borrar es Retroceso, y aun con Supr hacía falta
  seleccionar primero la arista.
- Las aristas eran la línea fina por defecto, de difícil selección, sin estado visual
  claro ni ninguna vía con ratón para eliminarlas.

La persistencia no era la causa: `handleSave` copia las aristas del lienzo al borrador
antes de guardar, así que lo eliminado no reaparece.

### Qué se modificó y por qué

- **`components/flow/DeletableEdge.jsx` (nuevo):** arista con `interactionWidth` de 28 px,
  trazo más grueso al seleccionarla y un botón «Eliminar» visible con `aria-label`. Usa
  `deleteElements({ edges: [{ id }] })`, que solo quita la arista y no los nodos. Se
  registra como tipo `default`, así que también cubre las aristas ya guardadas.
- **`FlowDesignerPage.jsx`:** `deleteKeyCode={['Backspace', 'Delete']}`, `edgeTypes`, y
  `ariaLabel` por arista («conexión de X a Y»).
- **`index.css`:** estilo del botón.

### Definition of Done

- [x] **AC1** la arista desaparece, los nodos permanecen y persiste al reabrir:
  `tests/test_flow_designer_edges.py` fija el cableado; el reducer de React Flow
  (`applyEdgeChanges`) se comprobó en Node (quita solo la arista indicada).
- [ ] **Prueba E2E** «crear → conectar → eliminar → guardar → reabrir»: **no hecha**, no
  hay runner de navegador en el repo. Pendiente para QA (Pantoja / Molina).

### Verificación

- `npm run build` OK; tests estructurales en verde. **No** se probó en navegador.

### Fuera de alcance / notas

- Deshacer/rehacer (opcional en el plan) no se implementó.
