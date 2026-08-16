# Tarea #249 — T11.3 Endpoint de vista previa server-side (body+tema → HTML)

## 2026-08-16 17:14 — Completada ✅

- **Rama:** `feat/249-paper-preview-endpoint`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #249`)
- **Spec/ADR:** SPEC-022, Épica E11. Criterio vinculante: **AC3** (parte server-side).
- **Dependencias:** #248 (T11.2) — implementada; esta rama la incluye.

### Qué se hizo

Nuevo **`POST /api/v1/articles/{id}/preview`**: renderiza la maqueta a partir de
**ediciones sin guardar** y **no persiste nada**.

**Por qué server-side** (clarify SPEC-022): usa exactamente la misma
`build_paper_html` que el paper publicado, así que la previa es **byte a byte**
lo que saldrá al imprimir a PDF. Reimplementar la maqueta en el navegador habría
creado una segunda fuente de verdad que se desincroniza.

**`PaperPreviewDTO`** con todos los campos opcionales (`title`, `body`,
`abstract`, `authors`, `scientific_format`, `theme`): lo que no se envía cae a lo
que el artículo ya tiene, de modo que el panel puede previsualizar **un solo
control cambiado** sin reenviar el documento entero.

**Cascada de tema** con la capa efímera como la más específica:
preset del formato → tema del proyecto → tema del artículo → **tema de la petición**.

**Visibilidad idéntica** a `get_article_paper`: una previa nunca revela un
artículo que quien llama no pudiera ya leer.

### Test nuevo

`backend/tests/test_paper_preview_endpoint.py` (12 casos):
- **previa == publicado**: el HTML es *idéntico* al de `build_paper_html` con los
  mismos datos;
- usa cuerpo/abstract/autores/formato **sin guardar**; los campos no enviados
  conservan el valor almacenado;
- tema efímero aplicado; **sobreescribe** el tema guardado; y si no se envía, se
  usa el guardado;
- **no persiste nada**: `commit` nunca se llama, `add` vacío y el objeto artículo
  queda intacto;
- visibilidad: 403 para lector ajeno a un borrador, permitido para el autor,
  404 si no existe.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_paper_preview_endpoint.py -q
# → 12 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 189 passed
```

### Definition of Done (AC3, parte server-side)

- [x] Endpoint que toma `body + metadata + theme` **sin persistir** y devuelve el
  HTML de `paper_layout` (única fuente de verdad: previa == PDF).
- [x] Tests en verde (12 nuevos; 189 en la suite).
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Siguiente

La otra mitad de AC3 —repintado con *debounce* ≤ 1 s— es **T11.4 (#250)**, que
consume este endpoint desde el panel de personalización.
