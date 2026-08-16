# Tarea #250 — T11.4 Panel de personalización en la UI con vista previa en vivo y edición de texto

## 2026-08-16 17:32 — Completada ✅

- **Rama:** `feat/250-customization-panel`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #250`)
- **Spec/ADR:** SPEC-022, Épica E11. Criterios vinculantes: **AC3** y **AC4**.
- **Dependencias:** #248 (T11.2) y #249 (T11.3) — implementadas; esta rama las incluye.

### Qué se hizo

Nueva vista **`/articles/:id/design`** (`PaperDesignPage.jsx`): controles de
presentación y edición de texto a la izquierda, **vista previa en vivo** de la
maqueta final a la derecha.

**Vista nueva, no dentro de `ArticleDetailPage`**: ese archivo ya tenía 595
líneas y la spec (§4) contemplaba «o vista nueva». Se enlaza desde Acciones del
artículo con el botón **«Diseñar paper»**.

**Controles** (todos de allowlist cerrada, nunca CSS libre):
- formato de cita (incluye el preset **ACL** de T11.1);
- tipografía (6 familias web-safe) con opción «(la del formato)»;
- acento: 7 muestras de color de los tokens del design system (E7);
- columnas: Una / Dos / **Auto** (Auto = las del formato de cita).

**Edición de texto** (AC4): título, abstract y cuerpo markdown, sobre el mismo
`updateArticle` que ya existía, de modo que la publicación usa lo editado.

**Previa en vivo** (AC3): *debounce* de **400 ms** tras el último cambio —bien
por debajo del segundo que exige el AC— y llamada a `POST /articles/{id}/preview`
(T11.3), que renderiza con la misma función que el paper publicado.

### Decisiones documentadas

- **Guarda contra respuestas fuera de orden**: cada render lleva un número de
  secuencia (`requestSeq`) y solo se pinta si sigue siendo el más reciente. Sin
  esto, una petición lenta podía sobreescribir una previa más nueva —un fallo
  clásico e intermitente en previas con debounce.
- **`sandbox=""` en el iframe de la previa**: la maqueta es HTML+CSS estático,
  no necesita scripts ni same-origin. Es el sandbox más restrictivo posible y se
  adelanta al endurecimiento de T2.2 (#160).
- **Las allowlists del frontend son un espejo, no la autoridad**: el backend
  valida de nuevo y descarta lo que no reconoce, así que una desincronización
  degrada al preset en vez de romper.
- **Botón Guardar deshabilitado si no hay cambios** (`dirty`), para que se vea
  qué está persistido y qué es solo previa.

### Verificación

```
npm run build && npm run build:public          # ambos OK
```

**Verificado en navegador** (Chromium sobre el stack real), midiendo *estilos
computados dentro del iframe* de la previa:

| acción | color de encabezado | columnas | tipografía |
|---|---|---|---|
| inicial | `rgb(11,27,51)` (ink) | 2 | Times New Roman |
| acento → violeta | `rgb(107,79,227)` | 2 | Times |
| columnas → Una | violeta | `auto` (1) | Times |
| tipografía → Helvetica | violeta | auto | **Helvetica** |

Y editando el cuerpo, la previa incorpora el texto nuevo. (El primer intento de
comprobación fue mío y era erróneo: comparaba solo el `<body>` del iframe, pero
acento y columnas viven en el `<style>` del `<head>`.)

### Definition of Done (AC3, AC4)

- [x] **AC3** — al cambiar texto o cualquier control, la previa se re-renderiza
  **sin publicar**, con debounce de 400 ms (≤ 1 s). Se genera **server-side**
  reutilizando `paper_layout` (previa == PDF).
- [x] **AC4** — se editan cuerpo/título/abstract y `updateArticle` los persiste;
  la publicación usa la versión editada. Controles: fuente (allowlist web-safe),
  acento (tokens E7) y columnas.
- [x] `npm run build` y `npm run build:public` OK.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Fuera de alcance

**T11.5 (#251)** — imágenes/figuras subibles e insertables — es la última tarea
de E11 y depende además de T2.3/#161 (validación por *magic bytes*).
