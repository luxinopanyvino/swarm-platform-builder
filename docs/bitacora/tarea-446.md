# Tarea #446 — T20.14 Frontend: estado del artículo, informe de compuerta y aprobación

## 2026-10-21 — Parcial 🟡 (implementado y construido; sin verificar en navegador)

- **Rama:** `feat/t20-14-frontend-compuerta`
- **PR:** la de esta rama → `develop` (`Closes #446`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC6, AC7, AC8 y AC14 · épica E20 (#432)
- **Dependencias:** T20.6 (#438) y T20.10 (#442), ya en `develop`

### Dónde estaba el problema

El backend ya devolvía `requires_human_review`, el informe de la compuerta, los códigos 409 de `approve`/`publish`
y los eventos SSE `gate_failed` y `requires_human_review`, pero la interfaz no los conocía: un artículo en el estado
nuevo salía como «Borrador», el informe no se veía, un 409 se mostraba como «Error al aprobar» y no había forma de
declarar al autor responsable (sin el cual no se puede aprobar).

### Qué se hizo y por qué

Todo en `frontend/src/projects/alejandria-magazine/` (la plataforma no importa de aquí; hay un test que lo comprueba):

- `gate.js` (nuevo): etiquetas de criterios y estados, mensajes accionables por **código** de error
  (`no_responsible_author`, `text_changed`, `gate_blockers`, `review_missing`…) y `describeApiError`, que acepta
  `detail` como texto o como `{code, message}`. Los nombres de agente salen del catálogo del proyecto (`agentMeta`),
  no de una copia nueva.
- `components/GateReportPanel.jsx` (nuevo): por criterio, si se supera, la evidencia, el **agente al que le
  corresponde** y, aparte, los criterios aún sin comprobar con su fase. Dice «Sin informe» (artículos antiguos), avisa
  si el informe es de un texto anterior y permite **reevaluar**. Si el informe no carga, lo muestra con «Reintentar» en
  lugar de tragarse el error.
- `ArticleDetailPage`: estado «Requiere revisión humana» con sus comentarios del Revisor (`rejection_comment`) y qué
  hacer; panel de la compuerta; tarjeta de **autor responsable** («Declararme autor responsable»); las acciones de
  aprobar, publicar y rechazar traducen el error de la API; el revisor puede **rechazar** desde `requires_human_review`.
- `ArticlesPage`: el estado nuevo con su etiqueta y una pestaña «Revisión humana».
- `ExecutionPage`: atiende los eventos `gate_failed` (bloqueantes y agente responsable) y `requires_human_review`
  (puntuación y comentarios) con un aviso y en el log.
- `api/articles.js` y el store: `gate-report` (GET/POST) y `responsible-author`.
- **Corrección de un fallo previo:** `articlesApi.reject` mandaba el comentario en el cuerpo JSON, pero el backend lo
  declara como parámetro de consulta (`comment: str`), así que rechazar daba 422. Ahora va como `params`. Sin esto,
  «rechazar» desde `requires_human_review` (AC7) no habría funcionado.

### Definition of Done

- [x] `npm run build` y `npm run build:public` pasan.
- [x] Tests estructurales: `backend/tests/test_frontend_gate.py` (10) —cada valor de `ArticleStatus`, cada código de
  409 del backend, los cuatro estados de criterio y los dos eventos SSE están cubiertos por la interfaz—. Suite: 1361
  pasados; los mismos 4 fallos que `develop`.
- [ ] **Comprobación visual en el navegador: no hecha.** No hay test runner de frontend y no he abierto la interfaz;
  los tests prueban cobertura, no que se vea bien. Hay que revisar a mano: el panel en la barra lateral de 280 px,
  el aviso de la ejecución y la pestaña nueva.
- [ ] Falta una acción de «reejecutar» propia desde `requires_human_review`: se usa el flujo de ejecución existente.

### Verificación

Builds de Vite y lectura estructural del JSX. Sin navegador, sin QA.

### Fuera de alcance / notas

- Hay dos fallos preexistentes en `test_frontend_layers.py` que **no son de este cambio**: comparan rutas con `/`
  y en Windows salen con `\` (`platform\components\agents\AgentEditorModal.jsx`). Pasan en Linux/CI.
- No hay entrada para aportar el DOI de una referencia a mano desde la interfaz (CHK009 sigue abierto).
- El aviso de la ejecución es efímero (estado de la página); lo persistente es el estado del artículo y el informe.
