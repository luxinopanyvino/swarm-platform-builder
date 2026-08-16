# Tarea #248 — T11.2 Tema editable (fuente/color/columnas) parametrizando el preset + persistencia por artículo

## 2026-08-16 17:03 — Completada ✅

- **Rama:** `feat/248-editable-paper-theme`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #248`)
- **Spec/ADR:** SPEC-022, Épica E11. Criterio vinculante: **AC2**.
- **Dependencias:** #247 (T11.1) — **cerrada y mergeada** (PR #267).

### Qué se hizo

El usuario puede personalizar la maqueta **eligiendo valores de una allowlist**,
nunca escribiendo CSS: el tema *parametriza* el preset determinista.

**Allowlists** (`paper_layout.py`):
- **Fuentes**: 6 familias **web-safe** curadas (times, georgia, palatino,
  helvetica, arial, verdana). Sin webfonts embebidas → imprime igual en todas
  partes (clarify SPEC-022).
- **Color de acento**: 7 **tokens del design system** (E7,
  `frontend/ds/zeroheight/tokens.dtcg.json`): ink (default, casi negro y neutro
  para impresión), blue, violet, green, amber, red, teal. **No** se admite hex
  libre.
- **Columnas**: 1 o 2.

**`sanitize_theme(theme)`**: descarta —en vez de fallar— todo lo desconocido. Es
lo que hace cierto el AC2 («cae al valor por defecto sin romper la maqueta»)
también para temas guardados que quedaron obsoletos tras cambiar la paleta, o
que llegan de un cliente viejo. Rechaza `bool` explícitamente (es subclase de
`int`, así que `columns: True` habría colado como 1).

**`resolve_theme(*layers)`**: mezcla capas, la más específica al final. Cada capa
se sanea por separado para que una capa corrupta no envenene el resultado.

**Cascada completa (AC2)**: preset del formato → tema del proyecto → tema del
artículo. Las dos capas almacenadas las une `resolve_article_theme()` en el
router; el preset lo aplica `build_paper_html` como capa más ancha.

**Aplicación visual**: la fuente y las columnas sobreescriben el preset; el
acento colorea encabezados (`h1`–`h4`) y enlaces del cuerpo.

**Persistencia**: nueva columna `theme` (JSON) en `articles` **y** en `projects`,
más `ThemeDTO` en la entrada y `theme` en la respuesta del artículo. El
`UpdateArticleDTO` sanea al guardar y el layout vuelve a sanear al renderizar
(defensa en profundidad).

### Decisiones documentadas

- **Migración ad hoc, no Alembic.** SPEC-022 §7 preveía Alembic (T4.1/#168), que
  sigue abierta. Se sigue el patrón vigente del repo (`ALTER TABLE … ADD COLUMN`
  en `init_db`, en try/except), con un comentario de que converge con T4.1
  cuando aterrice. Alternativa descartada: adelantar Alembic desde esta tarea.
- **El `paper_html` almacenado sigue teniendo precedencia.** Es el artefacto
  publicado y no se regenera al cambiar el tema; el tema se aplica siempre que
  la maqueta se genera al vuelo (borradores y, con T11.3, la vista previa), que
  es donde vive el flujo de edición.
- **Validación permisiva en el DTO, estricta en el layout**: `ThemeDTO` acepta
  strings y el filtrado real ocurre en `paper_layout`, que queda como **única
  fuente de verdad** de lo permitido. Evita dos listas que se desincronizan.

### Test nuevo

`backend/tests/test_paper_theme.py` (24 casos):
- **override del preset**: fuente, columnas en ambos sentidos (apa 1→2 col,
  ieee 2→1), acento en encabezados/enlaces, acento por defecto = token ink;
- **AC2 — valores inválidos**: fuente fuera de la lista, **hex crudo**, nombre de
  color CSS, columnas 0/5, `True` como columnas, tipos no-string → todos
  descartados **y** el HTML resultante es *idéntico* al no tematizado;
- temas que no son dict (`None`, `""`, lista, número) ignorados;
- tema parcial: solo cambia la clave dada;
- **intento de inyección CSS** en fuente y color → descartado, sin rastro en el HTML;
- **cascada**: el artículo gana sobre el proyecto, una capa inválida no pierde la
  válida, cascada vacía;
- salida determinista.

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_paper_theme.py -q
# → 24 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 177 passed (suite completa, sin regresiones)
```

### Definition of Done (AC2)

- [x] **AC2** — el tema `{font, accent_color, columns}` sobreescribe el preset y
  queda **persistido con el artículo**; un valor no permitido **cae al valor por
  defecto sin romper la maqueta**; los defaults se **heredan del proyecto**
  (cascada preset → proyecto → artículo).
- [x] Tests que cubren el cambio, en verde (24 nuevos; 177 en la suite).
- [x] Sin secretos ni PII en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.

### Siguiente

Desbloquea **T11.3 (#249)**, el endpoint de vista previa server-side, que
reutiliza `build_paper_html` con el tema sin persistir.
