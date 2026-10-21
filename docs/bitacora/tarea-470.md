# Tarea #470 — Línea de etapas y reevaluación automática de la compuerta

## 2026-10-22 — Éxito ✅

- **Rama:** `feat/compuerta-etapas-reevaluacion` (parte de la de #469, que parte de la de #468: hasta que se fusionen, incluye sus commits)
- **PR:** la de esta rama → `develop` (`Closes #470`)
- **Origen:** seguimiento de SPEC-032 / E20 (#432). Para validar el flujo de punta a punta hacía falta ver de un vistazo en qué etapa está el
  manuscrito, y que el informe no se quedara viejo tras editar el texto.

### Qué se hizo y dónde

- **`gate.js` → `stageStates`:** deriva las etapas Investigador → … → Publicador (las del catálogo del proyecto) + Compuerta + Aprobación humana +
  Publicado. Cada una `done`/`current`/`failed`/`pending`: los agentes, por su última ejecución (`running`/`completed`/`failed`); la compuerta,
  por el informe (sin informe pendiente, texto cambiado en curso, con bloqueantes con problemas); la aprobación, por el estado del artículo.
  El Revisor muestra su puntaje (`82/100`) leído de la revisión guardada en el informe.
- **`components/PipelineStages.jsx`:** lista accesible (`<ol>` con `aria-label` por etapa), sin color como único indicador (icono + texto).
- **`ArticleDetailPage.jsx`:** carga las ejecuciones del artículo para la línea; si no cargan, la línea sale «pendiente» sin mostrar un error
  (no es información crítica). Tras **guardar el texto**, si ya había informe y quien edita es autor/revisor, **reevalúa solo**; si falla lo dice.
- No se tocó el backend.

### Definition of Done

- [x] `npm run build` y `npm run build:public` pasan; lints de tokens y estados async en verde.
- [x] La lógica de `stageStates` y `nextStep` se comprobó en Node con casos (agente reejecutado, revisión con puntaje, compuerta limpia, sin informe).
- [ ] Prueba manual en el navegador (línea de etapas y reevaluación tras editar): pendiente de quien revisa.
- [ ] La CI de esta PR es la comprobación en Linux.

### Fuera de alcance / notas

- Reevaluar tras una reejecución del pipeline: el pipeline ya guarda un informe nuevo al terminar; la página lo recoge al abrirla.
- No hay tests de JS en este repo (la suite del frontend es estructural, en Python); la lógica nueva se cubrió con la comprobación manual en Node de arriba.
