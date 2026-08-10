# Tarea #171 — T5.1 Logging estructurado (JSON) + correlation IDs

## 2026-08-10 15:57 — Completada ✅

- **Rama:** `feat/171-structured-logging`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #171`)
- **Spec/ADR:** SPEC-019 (Observabilidad), Épica E5. Criterio vinculante: **AC1**.
- **Dependencias:** Ninguna. (Desbloquea #172 T5.2, #173 T5.3 y #221 T9.1.)

### Qué se hizo

Base de observabilidad: logging **estructurado** con **id de correlación** por
request, según SPEC-019 §4 (JSON en prod, humano en dev; middleware ASGI).

**`app/core/logging_config.py`** (nuevo):
- `request_id_ctx` (`ContextVar`) — id de correlación del request/tarea; `"-"`
  fuera de un request.
- `RequestIdFilter` — inyecta `request_id` en **cada** registro.
- `JsonFormatter` — una línea JSON con `timestamp` (ISO-8601 UTC), `level`,
  `logger`, `message`, `request_id` y **campos contextuales** (`extra=` se promueve
  a claves de primer nivel); incluye `exc_info` cuando hay excepción.
- `HumanFormatter` — línea legible para dev (`DEBUG=true`), también sin emojis a
  INFO+.
- **Sin emojis a INFO+**: `strip_emojis()` elimina pictogramas/emoji (`🔍`, `✅`,
  `🎉`, …) en registros `INFO` y superiores; a `DEBUG` se conservan. El rango del
  regex es **conservador**: no toca puntuación ni acentos (em-dash `—`, elipsis
  `…`, tildes se preservan).
- `configure_logging(debug=None)` — instala el handler raíz (idempotente); JSON si
  no hay debug, humano si `settings.DEBUG`; baja el ruido de `uvicorn.access`/
  `httpx`/`httpcore` a WARNING.
- `request_id_middleware` — reutiliza `X-Request-ID` entrante (preserva el id de
  un gateway/cliente) o genera uno nuevo (uuid4 hex), lo fija en `request_id_ctx`
  durante todo el request y lo devuelve en la cabecera de respuesta; **resetea el
  contexto siempre** (incluso si el handler lanza), evitando fugas entre requests.

**`app/main.py`:** `configure_logging()` se llama al importar (lo antes posible,
para que el logging de runtime use el handler central) y el middleware se registra
con `app.middleware("http")(request_id_middleware)` **antes** que CORS.

### Decisiones

- **No se editan uno a uno los logs con emoji** de `use_cases.py`/adapters/routers:
  el saneo es **central** en el formatter (a INFO+), lo que garantiza AC1 sin tocar
  decenas de llamadas y sin afectar a los mensajes **SSE** de usuario (que no pasan
  por `logging`, son eventos del stream).
- **JSON vs humano** por `DEBUG` (SPEC-019 riesgo "verbosidad JSON en dev").
- Sin dependencias nuevas (stdlib `logging`/`json`/`contextvars`).

### Test nuevo

`backend/tests/test_logging_structured.py` (11 casos, sin FastAPI):
- JSON válido con `timestamp`/`level`/`logger`/`message`/`request_id`;
  `request_id` desde el `ContextVar`; `extra=` promovido; `exc_info` incluido.
- emojis eliminados a INFO+ y conservados a DEBUG; puntuación/acentos preservados;
  `HumanFormatter` sin emojis a INFO+ y con `request_id`.
- middleware: genera id y lo liga al contexto durante `call_next`, lo devuelve en
  la cabecera y **resetea** el contexto después; reutiliza el `X-Request-ID`
  entrante; resetea el contexto **aunque el handler falle**.

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest \
    tests/test_logging_structured.py -q                      # → 11 passed
python -m py_compile app/main.py app/core/logging_config.py  # OK

# smoke (formatter JSON):
… → {"timestamp":"…","level":"INFO","logger":"smoke",
     "message":"Investigando el tema — con acento…","request_id":"demo-req-1",
     "agent":"investigador","model":"claude-opus-5"}
# (emoji 🔍/✅ eliminados; em-dash y elipsis preservados; extra promovido)
```

### Definition of Done (AC1)

- [x] **AC1** — salida JSON estructurada con `timestamp`, `level`, `logger`,
  `request_id` (propagado por middleware) y campos contextuales; sin emojis a
  INFO+. Verificado por tests y smoke.
- [x] Tests que cubren el cambio, en verde (11 passed).
- [x] Sin secretos ni PII en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.

### Nota

Habilita las tareas siguientes de E5: **#172** (métricas Prometheus, tokens LLM por
agente/modelo) y **#173** (tracing OTel) consumen esta correlación; **#221**
(SPEC-014, traza de explicabilidad) reutiliza el `request_id`.
