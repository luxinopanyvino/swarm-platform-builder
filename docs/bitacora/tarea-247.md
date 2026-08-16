# Tarea #247 — T11.1 Preset de maquetación conferencia (ACL, 2 columnas) en paper_layout

## 2026-08-16 14:01 — Completada ✅

- **Rama:** `feat/247-acl-paper-preset`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #247`)
- **Spec/ADR:** SPEC-022 (Maquetación editable del paper), Épica E11.
  Criterio vinculante: **AC1**.
- **Dependencias:** Ninguna.

### Qué se hizo

Nuevo preset **`acl`** (estilo conferencia de la familia *ACL) en el generador
determinista `backend/app/modules/agents/adapters/paper_layout.py`.

**Preset** (`_FORMAT_STYLE["acl"]`): 2 columnas, `Times New Roman` serif, 10 pt,
interlineado 1,18, título 17 pt. Añade dos banderas de estilo *opt-in*:
`numbered_sections` y `hanging_references`.

**Numeración por contadores CSS** (`_numbering_css`): el contenedor `.paper-body`
inicializa `counter-reset: section`; cada `h2.section-heading` incrementa la
sección y reinicia la subsección; los `h3.subsection-heading` renderizan `N.M`.
Nada de números escritos a mano en el HTML.

**Sangría francesa en referencias**: `h2.references-heading ~ p` recibe
`padding-left: 1.2em; text-indent: -1.2em` — la primera línea queda a bandera y
las siguientes sangradas, como exige el estilo de conferencia.

**Decorado de encabezados** (`_decorate_headings`): marca cada `h2` como
`section-heading` o, si su texto es una etiqueta de referencias
(Referencias / References / Bibliografía / Bibliography / Works cited /
Literatura citada), como `references-heading` — que queda **excluido de la
numeración** (`content: none`) porque la lista de referencias es una sección sin
número.

**Formateador**: se añade `acl` a `_FORMAT_LABELS` y `_FORMAT_INSTRUCTIONS`
(citas autor-año, `(Autor et al., Año)`), coherente con la convención ACL.

### Decisiones documentadas

- **Se elimina la numeración manual del encabezado cuando el formato numera solo.**
  Los cuerpos que produce el Redactor/Formateador suelen traer `## 3. Arquitectura`;
  con el contador activo el resultado habría sido «3. 3. Arquitectura».
  `_MANUAL_NUMBER_RE` retira el prefijo `N.` / `N.M` únicamente en los formatos
  auto-numerados. Verificado por test y visualmente.
- **Los demás formatos quedan byte-idénticos.** El decorado y el CSS extra solo se
  aplican si el preset activa las banderas, así que `apa`, `ieee`, `vancouver`,
  `chicago` y `nature` no cambian su salida (hay tests de regresión que lo fijan).
- **El `acl` todavía no es seleccionable de extremo a extremo** — ver "Fuera de
  alcance". La tarea entrega la capacidad de maquetación (que es lo que pide AC1).

### Fuera de alcance (seguimiento propuesto)

Para que un usuario pueda **elegir** `acl` desde la UI faltan tres piezas que
**no** entran en AC1 y que arrastran una decisión de migración:

1. `ScientificFormat.ACL = "acl"` en `backend/app/models/enums.py`. La columna es
   un `SA_Enum`: en **PostgreSQL** (el `DATABASE_URL` por defecto de producción)
   añadir un valor exige `ALTER TYPE … ADD VALUE`, es decir, una **migración**.
   Alembic aún no está adoptado — es la tarea **T4.1 (#168)**, abierta.
2. La opción `<option value="acl">` en `frontend/src/components/agents/AgentEditorModal.jsx`.
3. Sincronizar el comentario de invariante del enum ("must stay in sync with the
   formateador adapter").

Se deja como seguimiento explícito en vez de romper despliegues Postgres o
adelantar la adopción de Alembic desde esta tarea.

### Test nuevo

`backend/tests/test_paper_layout_acl.py` (18 casos, deterministas y sin navegador):
- **AC1**: 2 columnas (`column-count: 2`), serif Times, `text-align: justify`;
  contadores CSS presentes (`counter-reset` / `counter-increment` /
  `content: counter(section)` y `N.M` para subsecciones); encabezados etiquetados;
  sangría francesa (`text-indent: -1.2em` + `padding-left: 1.2em`).
- numeración manual eliminada (sin `1. Introducción` duplicado);
- referencias no numeradas y reconocidas en 3 idiomas/etiquetas;
- **regresión**: los otros 5 formatos no se decoran ni numeran y conservan su
  numeración manual; `ieee` sigue a 2 columnas y `apa` a 1;
- formato desconocido cae al default; salida **determinista** (idempotente).

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_paper_layout_acl.py -q
# → 18 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 137 passed (suite completa, sin regresiones)
```

**Verificación visual** (fuera de la suite, con Chromium headless sobre el HTML
generado): render a 2 columnas con secciones «1 Introducción», «1.1 Motivación»,
«2 Trabajo relacionado», «3 Arquitectura del sistema», «3.1 Selección de modelo»,
«4 Resultados», «5 Conclusiones» — numeradas por CSS y sin duplicación — y
«Referencias» sin número con sangría francesa correcta.

### Definition of Done (AC1)

- [x] **AC1** — `scientific_format = "acl"` produce HTML a **2 columnas**, serif,
  **justificado**, con **secciones numeradas por contadores CSS** y **referencias
  con sangría francesa**; verificable sobre marcadores estructurales/CSS sin
  navegador.
- [x] Tests que cubren el cambio, en verde (18 nuevos; 137 en la suite completa).
- [x] Sin secretos ni PII en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.
