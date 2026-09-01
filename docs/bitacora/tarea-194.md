# Tarea #194 — T7.3 Estados consistentes de carga / vacío / error

## 2026-09-01 — Completada ✅

- **Rama:** `feat/194-estados-consistentes`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #194`)
- **Spec/ADR:** SPEC-003, Épica E7. Criterio vinculante: **AC4**. Cierra además
  **AC5**, y con él la épica completa.
- **Dependencias:** T7.1 (#192), ya integrada — los estados usan sus tokens.

### Qué se hizo

**`frontend/src/components/ui/states.jsx`** — `LoadingState`, `EmptyState`,
`ErrorState` y el compositor `AsyncState`, los tres que nombra SPEC-003 §4.
Adoptados por **14 vistas**, que son todas las que piden datos a la red.

**Los stores guardan el error.** `articleStore` y `flowStore` declaraban un campo
`error` que **no escribían nunca**; `projectStore` sí lo escribía pero nadie lo
leía. Ahora los tres lo guardan y las páginas lo consumen.

**`scripts/check_async_states.py`** en la CI, que es lo que convierte AC5 de
«checklist» en comprobación.

### El fallo que motiva la tarea

No es que los estados fueran inconsistentes. Es que **el estado de error no
existía**.

Todas las cargas seguían el mismo patrón: `catch { setLoading(false) }` más un
`toast.error(...)`. El toast desaparece a los pocos segundos, y lo que queda en
pantalla es el estado **vacío**:

> Sin artículos — ejecuta un pipeline desde el Flow Designer para generar tu
> primer artículo.

Es decir: con el backend caído, la aplicación afirma que no tienes datos cuando
lo que ocurre es que **no ha podido preguntarlo**, y no ofrece reintentar. La
única salida era recargar la página entera.

Los sitios donde más duele:

- **`MagazinePage`** es la portada **pública**, la que ve alguien que llega de
  fuera. Su carga era `.catch(() => {})`: un backend caído se leía como «no hay
  artículos publicados aún». Peor mentira, y al público.
- **`ArticleDetailPage`** enseñaba «**Artículo no encontrado**» ante cualquier
  fallo de carga. Eso es una afirmación sobre el artículo cuando lo único que se
  sabe es que la petición falló.
- **`AgentsPage`** ya intuía el problema y lo resolvía adivinando: «No se
  encontraron perfiles. **Comprueba que el backend está en ejecución.**» — un solo
  mensaje para los dos casos, porque no sabía cuál era.

### Decisiones documentadas

- **Si hay datos, se enseñan los datos.** Es la única regla de `AsyncState` por
  encima de las demás: ni el spinner ni el error tapan una lista que ya se puede
  leer. Cubre dos casos reales — recargar una lista ya cargada (sin parpadeo) y
  fallar al refrescar cuando `flowStore` tiene flujos cacheados en
  `localStorage`, donde tirar esa lista para enseñar un error sería peor que el
  error.
- **Error antes que vacío.** El orden de comprobación importa: al revés, una
  lista vacía por un fallo de red se pinta como «no hay nada» y el error no llega
  a verse nunca. Es exactamente el orden que estaba mal escrito.
- **El vacío no es una alerta.** `EmptyState` no lleva reintento ni `role="alert"`
  ni color de aviso: no ha fallado nada. Su acción, cuando la tiene, es el
  siguiente paso natural (crear el primero), no un «reintentar» disfrazado.
- **Un solo sitio traduce el error a un mensaje** (`src/api/errors.js`). Si cada
  store lo resuelve a su manera, la mitad acaba enseñando `[object Object]` y la
  otra mitad se traga el `detail` del backend, que es justo el que explica el
  porqué.
- **Los fallos ignorables siguen siendo ignorables, pero lo dicen.** Hay nueve
  `catch` mudos legítimos: el desplegable de modelos (que tiene valor por
  defecto), el sondeo de notificaciones cada 30 s (avisar en cada vuelta sería
  peor que el fallo), el refresco del artículo cuando el SSE ya lo trajo, y los
  eventos SSE ilegibles. Cada uno lleva ahora un comentario `mejor-esfuerzo:` con
  su razón, y el lint exige esa marca. Una excepción escrita es revisable; un
  `catch {}` mudo no.
- **La `Estado:` de SPEC-003 no se toca.** Con esta tarea sus cinco criterios
  quedan cumplidos, pero pasar la spec a Done es estado de ejecución, y eso lo
  decide el mantenedor al cerrar los issues (GOVERNANCE §3.1).

### Test nuevo

`backend/tests/test_async_states.py` (15 casos):
- **Estructural**: existen los cuatro componentes; el lint pasa; está en la CI;
  y los tres stores **escriben** su `error` y no solo lo declaran.
- **La guardia muerde**: se siembra un fichero con un estado pintado a mano y
  otro con `.catch(() => {})`, y se comprueba que el lint falla nombrándolos.
- **Y no da falsos positivos**: un `catch` marcado con `mejor-esfuerzo:` pasa, y
  un comentario que **menciona** `.catch(() => {})` al explicar por qué no se hace
  no cuenta como usarlo.
- **En Chromium**, sobre los componentes reales: cargando se anuncia con
  `role="status"` + `aria-live` y con texto (un spinner solo no dice nada a quien
  no lo ve, y el spinner va `aria-hidden`); el vacío **no** se anuncia como
  alerta y el error **sí**; el error **no se parece al vacío** (se compara el
  color computado del título y el texto); el botón de reintentar vuelve a lanzar
  la carga de verdad; y los datos ganan a cualquier estado.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 609 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

python3 scripts/check_async_states.py     # → [OK]
python3 scripts/check_contrast.py         # → [OK] 68 pares AA en claro y oscuro
python3 scripts/check_design_tokens.py    # → [OK]
npm run build && npm run build:public     # → ambos OK
python3 scripts/validate_specs.py         # → [OK]
```

Revisión visual en Chromium de los tres estados: el de error se distingue del
vacío por color, icono, texto y por llevar botón de reintento. Se añadieron
además al medidor de contraste los cuatro pares nuevos (título e icono de error,
título y descripción del vacío): 68 pares en AA.

### Definition of Done

- [x] **AC4** — las 14 vistas con datos remotos muestran cargando / vacío / error
  desde los mismos componentes, con reintento en el error.
- [x] **AC5** — los cuatro criterios anteriores tienen comprobación automatizada,
  no lista de repaso: AC1 `check_design_tokens.py`, AC3 `check_contrast.py`,
  AC4 `check_async_states.py`, AC2 los tests de teclado de T7.2.
- [x] Tests que cubren el cambio, en verde (15 nuevos; 609 en la suite).
- [x] Builds de frontend en verde, las dos.
- [x] Docs: SPEC-003 anotada y con sus cinco criterios marcados.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

- **Con esta tarea la épica E7 queda completa** (T7.1 #192, T7.2 #193, T7.3
  #194). Cuando el mantenedor cierre los issues, SPEC-003 puede pasar a `Done`.
- **`ExecutionPage` y `FlowDesignerPage` conservan lógica de estado propia** para
  el SSE (`pipelineFailed`, `cancelled`, logs). Es un estado de **ejecución**, no
  de carga de datos: cae fuera de AC4 a propósito.
- **Los `catch` de escritura siguen usando `toast`** (guardar, borrar, aprobar).
  Ahí el toast es lo correcto: la acción la ha lanzado una persona y el aviso
  responde a lo que acaba de hacer. El lint no los toca.
- Sigue pendiente de #193: **devolver a zeroheight los cambios de
  `ds/colors_and_type.css`**, o la siguiente regeneración reintroduce los pares
  de contraste que fallaban.
