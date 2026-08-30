# Tarea #174 — T5.4 /health liveness/readiness con chequeo de dependencias

## 2026-08-30 11:40 — Completada ✅

- **Rama:** `feat/174-167-health-readiness` (junto con #167)
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #174`)
- **Spec/ADR:** SPEC-019, Épica E5. Criterio vinculante: **AC4**.
- **Dependencias:** ninguna. Va con **#167 (T3.5)** porque esa tarea necesita este
  endpoint: sus healthchecks de readiness no tenían qué consultar.

### Qué se hizo

`app/routers/health.py` con los dos endpoints, sacados de `main.py`:

- **`GET /health`** — liveness. Mismo formato que antes (`{"status": "healthy",
  "service": "alejandria_backend"}`), porque ya lo consumían compose y scripts.
- **`GET /health/ready`** — readiness. Comprueba base de datos, Qdrant y proveedor
  de LLM, y devuelve **`503` con el detalle por dependencia** cuando algo falla.

```
liveness  HTTP 200
readiness HTTP 503
{"status":"not_ready","checks":{
  "database":{"status":"ok"},
  "qdrant":{"status":"error","reason":"no alcanzable"},
  "llm":{"status":"not_configured","provider":"anthropic","reason":"sin credencial"}}}
```

### Decisiones documentadas

- **El liveness no consulta dependencias, y es lo importante de la distinción.** Si
  lo hiciera, una caída de Postgres haría que el orquestador reiniciase el backend
  en bucle sin arreglar nada, tirando además las conexiones que sí funcionaban. Hay
  un test que revienta si alguien le añade un chequeo.
- **Los tres chequeos van en paralelo** (`asyncio.gather`) con timeout de 3 s. En
  serie, tres dependencias lentas sumarían sus esperas y el sondeo tardaría más que
  el intervalo de 15 s que lo invoca.
- **El chequeo de LLM sigue al proveedor configurado, no a Ollama.** AC4 se escribió
  cuando Ollama era el único motor; desde E12 el proveedor por defecto es Anthropic.
  Con un proveedor remoto **no se hace llamada de prueba**: costaría dinero en cada
  sondeo, y son cada 15 segundos. Se comprueba que haya credencial, que es como ese
  proveedor falla en la práctica. Con Ollama, local y gratuito, sí se sondea la red.
  Hay un test que falla si alguien introduce una petición a un proveedor de pago.
- **Sin autenticación**: quien lo consulta es el orquestador y no tiene
  credenciales; si exigiera token, el contenedor nunca se marcaría sano.
- **Y por eso no filtra nada.** El detalle se limita a un estado por dependencia:
  ni URLs, ni puertos, ni versiones, ni mensajes del motor, que serían un mapa de la
  infraestructura para quien no debe tenerlo. Hay test con una lista de filtraciones.
- **Un `401`/`403` de Qdrant se reporta distinto de una caída**: es una API key mal
  configurada, y el diagnóstico es completamente diferente.

### Test nuevo

`backend/tests/test_health_readiness.py` — la parte de AC4 (16 de los 26 casos):
liveness estable y **ciego a dependencias rotas**; readiness 200 con todo sano;
`503` nombrando la dependencia caída para cada una de las tres, sin dejar de
reportar las sanas —hace falta para saber qué **no** es el problema—; se reportan
**todos** los fallos, no solo el primero; no filtra detalle de infraestructura; no
pide autenticación; y el chequeo de LLM según proveedor.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_health_readiness.py -q
# → 26 passed (AC4 + AC5)
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 407 passed
```

Contra un servidor real con Qdrant ausente: liveness `200`, readiness `503`.

### Definition of Done (AC4)

- [x] **AC4** — `/health` distingue liveness de readiness; readiness comprueba BD,
  Qdrant y proveedor de LLM y devuelve `503` con el detalle de lo caído.
- [x] Tests que cubren el cambio, en verde.
- [x] Observabilidad: `event=readiness_check_failed` y `readiness_not_ready` en el
  log estructurado de T5.1.
- [x] Sin secretos ni PII en el diff.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

De **E5** quedan **#172 (T5.2, métricas Prometheus)** y **#173 (T5.3, tracing OTel,
fase 2)**.
