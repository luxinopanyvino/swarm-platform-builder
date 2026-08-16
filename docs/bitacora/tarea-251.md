# Tarea #251 — T11.5 Imágenes/figuras: subida validada (magic bytes) + inserción + render en la maqueta

## 2026-08-16 18:08 — Completada ✅

- **Rama:** `feat/251-paper-images`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #251`)
- **Spec/ADR:** SPEC-022, Épica E11. Criterio vinculante: **AC5**.
- **Dependencias:** #250 (T11.4) y **#161 (T2.3)** — ambas implementadas; esta
  rama parte de #161, que se resolvió como habilitador porque el AC5 dice
  literalmente «reutiliza la validación de T2.3» y estaba abierta.

### Qué se hizo

**Store de assets por proyecto** (`app/platform/assets.py`): las figuras viven en
un directorio **por `project_id`**, separado del RAG — Qdrant guarda embeddings,
no binarios, y mantenerlas fuera preserva el aislamiento por proyecto de E8.

**Referencia e inlining**: se referencian desde el cuerpo como
`![pie](asset:<id>)` y se **incrustan como data URI** al maquetar. Esa es la
decisión clave: el HTML del paper sigue siendo **autocontenido**, que es lo que
permite renderizarlo dentro del `sandbox=""` (sin same-origin, sin cookies) y
**imprimirlo a PDF sin peticiones adicionales**. Servirlas por URL habría
requerido cabecera de autorización que el iframe no envía.

**Subida validada** (`POST /articles/{id}/assets`): tamaño (máx. 5 MB) y
`validate_upload` de **T2.3** antes de escribir nada en disco, así que un payload
renombrado nunca llega al almacén. Devuelve el markdown listo para pegar.

**Render**: `<figure class="paper-figure">` con `<img>` y `<figcaption>`, con
`break-inside: avoid` para que no se parta entre columnas ni páginas.

**UI**: botón «Insertar imagen» en el panel de diseño (T11.4) que sube y añade
la referencia al cuerpo; la previa la muestra en el siguiente tick del debounce.

### Decisiones documentadas

- **Solo tres orígenes de imagen admitidos** (`_safe_img_src`): `asset:<id>`
  resuelto por el proyecto, `data:image/...` ya formado y `https://`. Se
  descartan `javascript:`, `data:text/html`, `http://` y `file://`. Un `<img>`
  no ejecuta `javascript:`, pero `data:text/html` sí es un vector real.
- **Resolver acotado al proyecto**: un artículo solo puede incrustar figuras de
  **su** proyecto, aunque el cuerpo referencie un id ajeno (hay test).
- **Referencia irresoluble → se descarta en silencio**, sin romper el párrafo
  que la contiene: un id borrado no debe reventar la maqueta.
- **`.assets/` añadido a `.gitignore`**: son binarios locales por máquina, como
  `.rag_local/`. Sin eso, las imágenes subidas acabarían versionadas.

### Test nuevo

`backend/tests/test_paper_figures.py` (22 casos):
- store: round-trip; **aislamiento entre proyectos**; asset inexistente;
  *traversal* (`../../etc/passwd`, absoluto, comillas) neutralizado en id y en
  project; parseo de referencias;
- **AC5**: la referencia se incrusta como data URI con `<figure>`/`<figcaption>`;
  la figura aparece en el paper completo junto con su CSS; figura de **otro
  proyecto** descartada; referencia inexistente descartada **sin romper el
  párrafo**;
- **orígenes inseguros** (`javascript:`, `data:text/html`, `http://`, `file://`,
  `vbscript:`) descartados; seguros conservados; **alt escapado**; los enlaces
  normales siguen funcionando junto a las imágenes; cuerpo sin imágenes idéntico
  con y sin resolver.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_paper_figures.py -q
# → 22 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 245 passed
npm run build && npm run build:public   # ambos OK
```

### Definition of Done (AC5)

- [x] **AC5** — contenido real que no corresponde a un tipo permitido → **400**
  (reutilizando T2.3); si es válida, se **almacena en un store por proyecto**
  (con `project_id`, separado del RAG), puede **insertarse** en el cuerpo como
  `![alt](ref)` y **aparece** en la maqueta y en el PDF.
- [x] Tests que cubren el cambio, en verde (22 nuevos; 245 en la suite).
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Cierre de la épica E11

Con T11.5, **E11 (Publicación y maquetación editable) queda completa**: preset
ACL (T11.1), tema editable (T11.2), preview server-side (T11.3), panel con previa
en vivo (T11.4) y figuras (T11.5).
