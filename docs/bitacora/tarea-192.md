# Tarea #192 — T7.1 Unificar colores en tokens de diseño

## 2026-09-01 — Completada ✅

- **Rama:** `feat/192-design-tokens`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #192`)
- **Spec/ADR:** SPEC-003, Épica E7. Criterios vinculantes: **AC1** y la mitad
  automatizable de **AC5**.
- **Dependencias:** ninguna. Es la base de T7.2 (#193) y T7.3 (#194).

### Qué se hizo

**82 colores hexadecimales literales sustituidos por tokens** en 11 ficheros de
`frontend/src`. El mapeo no fue mecánico: cada hex se resolvió al token cuyo
**significado** coincidía, no al que más se le parecía. Los cinco colores de
agente (`#0d9dda`, `#6b4fe3`, `#c47d04`, `#2e844a`, `#cb4b3f`) ya tenían token
propio (`--agent-research`, `--agent-write`, `--agent-review`, `--agent-format`,
`--agent-publish`) y estaban duplicados a mano en tres sitios distintos; el resto
cayó en la escala neutra, de estado (`--success`, `--warning`, `--error`) o de
marca.

**`scripts/check_design_tokens.py`** — la comprobación automatizable de AC5, en la
CI (job `frontend-build`, con el `python3` del runner: solo stdlib, no instala
nada).

**`frontend/src/paperTheme.js`** — extraída la lista de acentos del paper a un
módulo con su motivo escrito, porque es la única exención del lint.

### Lo que apareció al mirar de cerca

**ConfigPage pintaba con variables que no existen.** Usaba `var(--border-color,
#d0d7de)`, `var(--color-success, …)`, `var(--surface-2, …)` y tres más: ninguna
está definida en el design system ni en los shims. El color lo ponía **siempre el
fallback**; el `var()` era decorativo. Estaba tokenizado de mentira.

Eso llevó a la segunda regla del lint, y a buscar el mismo patrón sin fallback:
**seis usos de `var(--…)` a tokens inexistentes** (`--border-color` ×9 en tres
páginas, `--bg-app`, `--bg-input`, `--surface-secondary`, `--surface-tertiary`,
`--text-default`). Sin fallback, `var(--inexistente)` es inválido en tiempo de
cómputo: el navegador **descarta la propiedad** y el elemento hereda o vuelve al
valor inicial. No hay error, no hay aviso, y a simple vista parece código
tokenizado ejemplar. Un hex literal, comparado con esto, al menos es honesto.
Corregidos los seis contra el token real (`--border-default`, `--bg-canvas`,
`--bg-surface`, `--bg-sunken`, `--bg-inset`, `--text-body`).

### Decisiones documentadas

- **`paperTheme.js` queda exento, y el motivo se prueba.** Sus hexes son el
  espejo exacto de `_THEME_ACCENTS` en
  `backend/app/modules/agents/adapters/paper_layout.py`: son los colores del
  **paper impreso**, no los de la aplicación. Tokenizarlos daría una muestra que
  **miente** sobre el PDF que se va a generar, y que además cambiaría con el tema
  claro/oscuro del usuario mientras el PDF no cambia. Hay un test que compara
  ambas listas, para que la exención deje de ser válida en cuanto deje de ser
  cierta.
- **El lint valida dos cosas, no una.** AC1 pide «sin hex literal», pero cumplirlo
  con `var(--nombre-inventado)` es peor que no cumplirlo. La segunda regla cierra
  esa puerta.
- **Los comentarios no cuentan.** Se blanquean antes de buscar, conservando los
  saltos de línea para no mover los números de línea del informe. Mencionar un hex
  al explicar por qué ya no se usa no lo pinta.
- **Las excepciones llevan motivo obligatorio en el propio script** (un `dict`
  nombre → razón, que el script imprime al pasar). Una lista de exenciones sin
  razones se convierte en el sitio donde va lo incómodo.
- **`--paper-surface` es un token nuevo en `src/index.css`**, no `--bg-surface`:
  la hoja del paper es blanca **también en tema oscuro**, porque la vista de
  maquetación y su impresión son una hoja, no parte del chrome de la aplicación.
  Apunta a `--neutral-00`, que es blanco en ambos temas.
- **`ds/colors_and_type.css` no se toca.** Tiene un `#06101f` suelto en
  `[data-theme="dark"] .prose pre` (línea 342), pero AC1 acota a `frontend/src` y
  `ds/` es la capa de **definición** del design system, regenerada desde
  zeroheight. Anotado como seguimiento, no arreglado por la puerta de atrás.

### Test nuevo

`backend/tests/test_design_tokens.py` (12 casos):
- **AC1**: sin hexes literales; todos los `var(--…)` resuelven.
- **AC5 / la guardia muerde**: se **siembra** un fichero en `frontend/src` con un
  hex reintroducido, y otro con un token inexistente, y se comprueba que el lint
  falla nombrándolos. Un lint que solo se ejecuta sobre código limpio demuestra
  que hoy no hay hallazgos, no que sepa encontrarlos.
- **AC5 / falsos positivos**: un hex en un comentario y un token definido en los
  shims de `src/` (no en `ds/`) pasan.
- **AC5 / automatizada de verdad**: el workflow de CI invoca el script, y el
  script no importa nada fuera de la stdlib.
- **La exención sigue teniendo motivo**: `paperTheme.js` está en `EXCEPCIONES` con
  razón escrita, sus valores coinciden con `_THEME_ACCENTS` del backend, y
  `PaperDesignPage` consume la constante compartida en vez de una copia local.

### Verificación

```
python3 scripts/check_design_tokens.py
# → [OK] frontend/src: sin hex literales y todos los var(--…) resuelven.
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q      # → 587 passed
npm run build && npm run build:public                                 # → ambos OK
python3 scripts/validate_specs.py                                     # → [OK]
```

**Comprobado en navegador**, no solo por regex: se cargó el CSS **construido** en
Chromium y se leyó `getComputedStyle` de los **137 tokens** que usa
`frontend/src`, en `data-theme="light"` y `data-theme="dark"`. Ninguno resuelve a
vacío en ninguno de los dos temas. Es la comprobación que distingue «el token
existe en el fichero» de «el token pinta algo», que es justo la diferencia que
esta tarea destapó.

### Definition of Done

- [x] **AC1** — sin colores hexadecimales literales en `frontend/src`; todo color
  sale de un token del design system (una exención, documentada y probada).
- [x] **AC5 (parte automatizable)** — `scripts/check_design_tokens.py` valida AC1
  y corre en la CI. El checklist de AC2–AC4 llega con T7.2 y T7.3, así que AC5
  queda sin marcar en la spec.
- [x] Tests que cubren el cambio, en verde (12 nuevos; 587 en la suite).
- [x] Builds de frontend en verde, **las dos** (app principal y revista pública).
- [x] Docs: SPEC-003 anotada; el porqué de cada exención vive en el propio script.
- [x] Sin secretos ni PII en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

- **`ds/colors_and_type.css:342`**: `#06101f` en `[data-theme="dark"] .prose pre`.
  Fuera del alcance de AC1, pero conviene que la capa de definición tampoco tenga
  literales fuera de la paleta.
- **#193 (T7.2)** y **#194 (T7.3)** completan AC5: el checklist verificable de
  AC2–AC4. Esta tarea les deja los tokens sobre los que medir contraste (AC3) y
  con los que construir los estados loading/empty/error (AC4).
- **ConfigPage cambió de aspecto**, poco pero de verdad: sus colores los ponían
  fallbacks codificados a mano y ahora los ponen los tokens del tema. Es el
  comportamiento correcto —responde al tema oscuro, cosa que antes no hacía—, pero
  conviene mirarlo en la revisión visual de T7.2.
