# Tarea #162 — T2.4 Manejador global de excepciones (sin fugas de stack)

## 2026-08-17 08:05 — Completada ✅

- **Rama:** `sec/162-global-exception-handler`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #162`)
- **Spec/ADR:** SPEC-016, ADR-0003, Épica E2. Criterios vinculantes: **AC3** y **AC4**.
- **Dependencias:** ninguna declarada. Se apoya en **#171 (T5.1)**, ya mergeada:
  el diseño de la spec anticipaba «se integra con T5.1 cuando exista», y existe,
  así que el identificador de correlación es el mismo de T5.1 y no uno propio.

### Qué se hizo

**`app/core/errors.py` (nuevo)**: una excepción no controlada deja de llegar a
`ServerErrorMiddleware` de Starlette y produce siempre un `500` **opaco y
estable** — `detail` genérico + `request_id` — mientras el diagnóstico completo
(traza con `exc_info`, método, ruta y tipo de excepción) va al **log estructurado
de T5.1** con ese mismo `request_id`. El usuario puede citar un identificador y
soporte encuentra la traza exacta, sin que el detalle interno haya viajado nunca
por la red.

**Instalación en dos capas** (`install_error_handling`), no una:

1. **Middleware `catch_unhandled_errors`** — la ruta normal.
2. **`app.add_exception_handler(Exception, …)`** — red de seguridad para lo que
   estalle *fuera* del middleware (en CORS, o en el propio middleware de
   correlación).

No pueden ejecutarse los dos para la misma excepción: si el middleware responde,
no se propaga nada hacia arriba.

**`app/main.py`**: `install_error_handling(app)` se invoca **antes** de añadir el
middleware de correlación y CORS. En Starlette el middleware añadido más tarde
queda más al exterior, así que ese orden deja el de captura por dentro de ambos.

**`app/core/logging_config.py`**: el middleware de T5.1 ahora también deja el id
en `request.state.request_id` (una línea). Es aditivo y necesario: el manejador
registrado corre por encima de ese middleware, cuando el `ContextVar` ya se
restableció.

### Decisiones documentadas

- **El middleware va por dentro de CORS, y eso no es cosmético.** Un `Exception`
  handler registrado se ejecuta en `ServerErrorMiddleware`, que es la capa más
  exterior: su respuesta **no pasa por CORS**, así que el navegador ve un error
  de red opaco y el `request_id` no llega nunca al usuario que debía citarlo.
  Poniendo la captura por dentro, el `500` conserva las cabeceras CORS y el
  frontend puede leer el cuerpo. Hay test que fija ese orden (`labels.index`),
  porque es exactamente lo que un refactor de `main.py` rompería sin avisar.
- **Ni siquiera en `DEBUG` viaja el mensaje de la excepción.** Con `DEBUG=true`
  se añade solo `error_type` (la *clase*). El mensaje puede arrastrar
  credenciales o SQL — el smoke test usa a propósito
  `RuntimeError("connection to postgres://user:hunter2@db failed")` — y la traza
  completa ya está en el log, que es donde el desarrollador la va a leer.
- **Las `HTTPException` no pasan por aquí.** Las resuelve `ExceptionMiddleware`,
  interior a las dos capas; un `404` sigue siendo un `404` con su `detail`. Hay
  test.
- **No se intenta cubrir el fallo a mitad de stream (SSE).** Cuando `call_next`
  ya devolvió, las cabeceras salieron y no hay respuesta que sustituir; ese caso
  lo gestiona el generador del stream. Está documentado en el docstring en lugar
  de fingir una cobertura que no existe.
- **El `ContextVar` se vuelve a fijar alrededor del `logger.error`**, porque el
  filtro de T5.1 estampa `record.request_id` desde el `ContextVar` — pasarlo por
  `extra` no funcionaría, el filtro lo sobreescribe.

### Test nuevo

`backend/tests/test_global_exception_handler.py` (17 casos), sobre una app mínima
con **el mismo cableado y orden** que `app.main`:

- **AC3 / respuesta**: `500` en excepción de router y en `ZeroDivisionError`; el
  cuerpo no contiene el mensaje interno, ni el nombre de la excepción, ni
  `Traceback`, `File "`, `site-packages` ni `.py", line`; el payload en producción
  es **exactamente** `{detail, request_id}`; `error_type` solo con `DEBUG=true` y
  aun así sin el mensaje.
- **AC3 / correlación**: se reutiliza el `X-Request-ID` entrante; se genera uno
  si falta; el log lleva **el mismo id** que la respuesta (capturado con el filtro
  real de T5.1, no con `caplog`, que no lo aplica); el log conserva la traza
  completa y los campos contextuales (`event`, `http_method`, `path`,
  `exception_type`).
- **No regresión**: `HTTPException` intacta; respuestas correctas intactas; el
  `500` **lleva cabeceras CORS**.
- **Red de seguridad**: fallo en una capa exterior al middleware → responde el
  manejador registrado, igual de opaco; y recupera el id desde `request.state`
  cuando el `ContextVar` ya se restableció.
- **Cableado real**: `app.main` tiene el manejador registrado y el middleware
  puesto, y el de captura es **interior** a CORS y a correlación.

`test_logging_structured.py`: el doble `_FakeRequest` gana `state` (un `Request`
real siempre lo tiene) y se fija la nueva escritura de `request.state.request_id`.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_global_exception_handler.py -q
# → 17 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 262 passed
```

Smoke sobre la app real con `DEBUG=false` y una ruta que revienta con una cadena
tipo credencial:

```
status: 500
body  : {"detail":"Error interno del servidor. Contacta con soporte citando el identificador.",
         "request_id":"7737a5e9f7804458a92caac545cbc1dc"}
cors  : http://localhost:5173
xrid  : 7737a5e9f7804458a92caac545cbc1dc
leak? : False
```

Y en stdout, el log JSON de producción con `request_id` idéntico, `event`,
`http_method`, `path`, `exception_type` y la traza completa **incluyendo** la
credencial que no salió por la respuesta.

### Definition of Done (AC3, AC4)

- [x] **AC3** — excepción no controlada con `DEBUG=false` → `500` sin traza ni
  detalles internos, y error logueado con identificador de correlación.
- [x] **AC4** — tests representativos (17 nuevos; 262 en la suite, en verde).
- [x] Docs/spec: sin cambio de spec; SPEC-016 §4 ya describía este diseño.
- [x] Sin secretos ni PII en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Cierre de la épica E2

Con T2.4, las tres tareas adoptadas por SPEC-016 quedan hechas: saneamiento de
enlaces + `sandbox` (T2.2 / #160), validación de subidas por magic bytes
(T2.3 / #161) y manejador global de excepciones (T2.4 / #162).

Queda **#159 (T2.1, SSRF del scraper)** como huérfana: pertenece a
[SPEC-002](../specs/SPEC-002-scraper-ssrf-protection.md), hoy **Superseded**
porque el scraper se eliminó (`71e3923`). Decisión humana pendiente: cerrarla
como *not planned* o volver a declararla en SPEC-016.
