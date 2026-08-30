# Tarea #167 — T3.5 Límites de recursos + healthchecks de readiness

## 2026-08-30 11:40 — Completada ✅

- **Rama:** `feat/174-167-health-readiness` (junto con #174)
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #167`)
- **Spec/ADR:** SPEC-017, Épica E3. Criterio vinculante: **AC5**.
- **Dependencias:** en la práctica, **#174 (T5.4)**: un healthcheck de readiness
  necesita un endpoint de readiness que consultar. Por eso van en la misma rama.

### Qué se hizo

**Límites de recursos en los cinco servicios** (`deploy.resources.limits`), que
antes no tenía ninguno:

| Servicio | CPU | Memoria | Por qué |
|---|---|---|---|
| `ollama` | 4.0 | **8G** | Un modelo de 7B no cabe por debajo de ~6G; es el primero que hay que subir si el pipeline se queda corto |
| `qdrant` | 1.0 | 2G | Mantiene vectores en memoria; el techo crece con el corpus RAG |
| `postgres` | 1.0 | 1G | El pico real es el pool de conexiones |
| `backend` | 2.0 | 1G | uvicorn y el grafo; no carga modelos en proceso |
| `frontend` | 0.5 | 256M | Solo sirve estáticos con nginx |

**Healthchecks donde faltaban**: `backend` y `frontend` no tenían ninguno. El del
backend es de **readiness** (`/health/ready`, de #174), no de liveness.

**`depends_on` de Qdrant corregido**: tenía healthcheck pero el backend solo
esperaba a `service_started`, así que podía empezar a atender con Qdrant todavía sin
responder. Ahora es `service_healthy`.

### Decisiones documentadas

- **La sonda es un fichero, `backend/healthcheck.py`, no un `python -c` en el
  compose.** La primera versión era un one-liner con comillas anidadas atravesando
  YAML, shell y Python: ilegible y fácil de romper sin que nadie se entere — y **un
  healthcheck averiado no avisa, simplemente deja de proteger**. Como fichero se
  lee y se prueba; hay test que comprueba que un puerto cerrado da «no listo» sin
  lanzar excepción.
- **Se sonda con Python, no con `curl`/`wget`**: es lo único que la imagen del
  backend garantiza tener, y **T3.3 (#165)** va a quitarle el toolchain. Atarlo a
  `wget` habría hecho que esa tarea rompiera este healthcheck en silencio.
- **`start_period: 60s` en el backend**: el primer arranque aplica migraciones y
  siembra datos. Sin ese margen, el contenedor se marcaría insano antes de terminar
  de arrancar.
- **Readiness y no liveness en el healthcheck del backend**, que es lo que pide AC5
  explícitamente: así `depends_on: service_healthy` de otro servicio significa algo
  de verdad —«puede atender»— y no solo «el proceso existe».

### Test nuevo

`backend/tests/test_health_readiness.py` — la parte de AC5 (10 de los 26 casos):
los cinco servicios declaran límite de CPU y de memoria; los cinco declaran
healthcheck; el del backend apunta a la sonda de **readiness** y tiene
`start_period`; el script existe y responde «no listo» ante un puerto cerrado; el
backend espera a Qdrant **sano**; y Ollama tiene el mayor presupuesto de memoria,
que es la invariante que se rompería al recortar límites sin pensar.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_health_readiness.py -q
# → 26 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 407 passed
```

El comando del healthcheck se probó **contra un servidor real** antes de fijarlo:
con Qdrant ausente devuelve `exit 1` (readiness `503`) y el de liveness `exit 0`.

`docker compose config` no se pudo ejecutar aquí (no hay Docker en el entorno); el
compose se valida como YAML y por los tests que leen su estructura.

### Definition of Done (AC5)

- [x] **AC5** — todos los servicios declaran límites de recursos y healthchecks de
  readiness además de liveness.
- [x] Tests que cubren el cambio, en verde.
- [x] Sin secretos en el diff.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

De **E3** quedan **#165 (T3.3, contenedores no-root + imagen slim)** y **#166
(T3.4, compose dev/prod separados, TLS, cabeceras y CSP)**. Cuando se haga #165,
conviene comprobar que `python` sigue en la imagen final: es de lo que depende esta
sonda.
