# Tarea #413 — BUG-005 «Volver» en Diseño del paper requiere dos clics

## 2026-10-21 — Completada ✅ (causa probable, pendiente de confirmar en navegador)

- **Rama:** `fix/bug-005-volver-un-clic`
- **PR:** [#418](https://github.com/onpremialabs/swarm-platform-builder/pull/418) → `develop` (`Closes #413`)
- **Origen:** informe de pruebas funcionales; plan `plan_fix_alejandria_magazine.md`
- **Dependencias:** ninguna.

### Dónde estaba el problema

`frontend/src/projects/alejandria-magazine/pages/PaperDesignPage.jsx`. «Volver» hacía
`navigate(-1)`, que depende del historial de sesión. La vista previa es un
`<iframe srcDoc={html}>` que se repinta tras cada edición (con debounce). Cambiar el
`srcdoc` de un iframe ya cargado es una navegación del iframe y puede añadir entradas
al historial de sesión conjunto; `navigate(-1)` consumía esa entrada en el primer clic
(sin salir de la página) y solo el segundo clic volvía. Encaja con que ocurra «tras
editar», cuando ya hubo repintados.

**Esto es una hipótesis razonada a partir del código, no reproducida**: no hay
navegador disponible en esta sesión y el plan pedía reproducirla con DevTools.

### Qué se modificó y por qué

- **`handleBack`:** navega a un destino explícito, `/dashboard/articles/:id` (la ruta
  del detalle desde la que se llega), sin depender del historial. Si hay cambios sin
  guardar pide confirmación en ese mismo clic.
- **`key={previewKey}` en el iframe:** cada previa es un iframe nuevo. La primera
  navegación de un iframe recién creado sustituye a `about:blank` y no añade entrada,
  así que además se evita contaminar el botón «atrás» del navegador.

### Definition of Done

- [x] **AC1** un solo clic regresa a la pantalla prevista: garantizado por el destino
  explícito. `tests/test_paper_design_back.py` fija por estructura que no se usa
  `navigate(-1)`, que se avisa de cambios sin guardar y que la previa se remonta.
- [ ] **Confirmación en navegador:** pendiente de QA. Si el fallo persistiera con esta
  rama, la causa no es la del iframe.

### Verificación

- `npm run build` y `build:public` OK; tests estructurales en verde.

### Fuera de alcance / notas

- `PaperViewPage.jsx` y `ArticleDetailPage.jsx` también usan `navigate(-1)`. No se
  tocaron: el informe solo señala el diseño del paper.
- Posible parpadeo mínimo al remontar el iframe en cada repintado de la previa.
