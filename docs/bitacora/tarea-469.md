# Tarea #469 — Panel de la compuerta desplegable, con acciones y siguiente paso

## 2026-10-22 — Éxito ✅

- **Rama:** `feat/compuerta-panel-acciones` (parte de la de #468: hasta que esa PR se fusione, esta incluye sus commits)
- **PR:** la de esta rama → `develop` (`Closes #469`)
- **Origen:** seguimiento de SPEC-032 / E20 (#432). El panel decía «superado»/«no supera» sin explicar qué se comprobó ni cómo avanzar.

### Qué se hizo y dónde

- **`frontend/.../components/GateReportPanel.jsx`:**
  - Cada criterio es un `<details>` (abierto si bloquea). Superado → qué se comprobó, con la lista de referencias resueltas. Bloqueante → qué
    falta, a qué agente corresponde y botones de acción. Las acciones solo se ofrecen si quien monta el panel puede ejecutarlas.
  - Formulario para **aportar a mano el DOI** de una referencia que no se pudo resolver (nota: se comprueba igual).
  - Banner **«Siguiente paso»** (qué hacer ahora y el botón para hacerlo): evaluar, reevaluar si el texto cambió, corregir el primer
    criterio bloqueante o, sin bloqueantes, aprobar.
  - Los criterios aún sin comprobar dicen **qué dato les falta** (`PENDING_REASONS`).
- **`frontend/.../gate.js`:** `summaryLines`, `nextStep`, `ACTION_LABELS`, `PENDING_REASONS`. Tolera informes antiguos sin `summary`/`actions`.
- **`ArticleDetailPage.jsx`:** `Reejecutar desde <agente>` abre el modal de pipeline con los agentes **desde el responsable en adelante**
  preseleccionados (`handleOpenPipelineModal(fromAgent)`); `Editar el texto` abre el editor; el DOI se envía por la API nueva.
- **Backend:** `PUT /articles/{id}/gate-report/sources/{index}` (`{doi}`): pone el DOI en la referencia del índice del informe, reevalúa y
  guarda un informe nuevo. **El DOI no se da por bueno**: la compuerta lo resuelve y exige título, autores y año (AC3), así que no abre
  ninguna excepción. 422 si no tiene forma de DOI, 404 si no existe el índice, 403 si no es autor/revisor/admin, 409 si está publicado.
- **API y store** (`api/articles.js`, `store/articleStore.js`): `setSourceDoi`.
- **Tests:** `test_gate_source_doi.py` (3 casos: índice y normalización, validaciones, permisos y publicado) y un test estructural en
  `test_gate_explain.py` que falla si el backend emite una acción o declara un criterio pendiente que `gate.js` no explica.

### Definition of Done

- [x] `npm run build` y `npm run build:public` pasan; lints de tokens y estados async en verde; `test_frontend_gate` y `test_frontend_layers` en verde.
- [x] Tests nuevos en verde.
- [ ] Prueba manual en el navegador del panel (acordeones, DOI, reejecutar desde un agente): pendiente de quien revisa.
- [ ] La CI de esta PR es la comprobación en Linux.

### Fuera de alcance / notas

- La línea de etapas del pipeline y la reevaluación automática van en #470.
- «Reejecutar» abre el modal ya existente en vez de lanzar la ejecución directamente: la persona confirma qué agentes corren.
