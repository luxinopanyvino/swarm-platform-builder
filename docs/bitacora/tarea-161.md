# Tarea #161 — T2.3 Validar subidas por magic bytes/content-type

## 2026-08-16 17:52 — Completada ✅

- **Rama:** `sec/161-upload-magic-bytes`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #161`)
- **Spec/ADR:** SPEC-016 (AppSec), Épica E2. Criterio vinculante: **AC2** (+ AC4, tests).
- **Dependencias:** Ninguna.

### Qué se hizo

Nuevo módulo **`backend/app/platform/uploads.py`**: la subida se valida por su
**contenido real**, no solo por la extensión declarada.

- `sniff_type(raw)` reconoce por firma: **pdf, png, jpeg, gif, webp** y `"text"`.
  El texto solo se acepta si decodifica en UTF-8, no tiene bytes NUL y **no
  empieza por marcado** (`<html`, `<svg`, `<script`, `<?xml`, `<!doctype`) — ese
  marcado subido como `.txt`/`.md` es justo el vector de XSS almacenado.
- `validate_upload(filename, raw, allowed_extensions)` exige que el tipo
  detectado corresponda a la extensión, **antes** de extraer texto o indexar.
- Cableado en los **dos** endpoints de subida (`/rag/library/upload` y
  `/{agent}/rag/upload`), donde antes solo había allowlist de extensión + 10 MB.

**Sin dependencias nuevas**: las firmas que interesan son un puñado de prefijos
de bytes; `python-magic`/libmagic habría metido una dependencia nativa en la
imagen para esto.

### Decisiones documentadas

- **415 vs 400 son respuestas distintas a preguntas distintas**: 415 = «no
  admitimos ese tipo de archivo»; **400 = «este archivo no es lo que dice ser»**
  (lo que exige el AC2). Mezclarlas ocultaría el intento de suplantación.
- **Extensiones de imagen ya soportadas** (png/jpg/jpeg/gif/webp) aunque los
  endpoints actuales solo admitan documentos: es lo que consumirá **T11.5
  (#251)**, cuyo AC5 dice explícitamente «reutiliza la validación de T2.3».

### Test nuevo

`backend/tests/test_upload_magic_bytes.py` (34 casos): reconocimiento de los 6
tipos; rechazo de vacío/binario/ELF; **marcado nunca aceptado como texto** (4
variantes de XSS); documentos e imágenes válidos; **contenido que no coincide con
la extensión → 400** (texto como .pdf, PDF como .txt, imagen como .md, HTML como
.png, PNG como .jpg…); extensión no permitida → 415; nombre vacío; fichero vacío;
extensión en mayúsculas.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_upload_magic_bytes.py -q
# → 34 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 223 passed
```

### Definition of Done (AC2)

- [x] **AC2** — una subida cuyo contenido no corresponde a su extensión se
  **rechaza con 400 antes** de extraer texto o indexar.
- [x] Tests que cubren el cambio, en verde (34 nuevos; 223 en la suite).
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Siguiente

Desbloquea **T11.5 (#251)**, que reutiliza `validate_upload` para las imágenes
del paper.
