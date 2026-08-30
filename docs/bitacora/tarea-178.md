# Tarea #178 — T6.4 Audit log de acciones sensibles

## 2026-08-30 10:55 — Completada ✅

- **Rama:** `feat/178-audit-log`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #178`)
- **Spec/ADR:** SPEC-020, ADR-0002/0004, Épica E6. Criterio vinculante: **AC4**.
- **Dependencias:** ninguna declarada. Se apoya en **T5.1 (#171)**, ya mergeada: la
  spec dice que el audit log «se apoya en la correlación de SPEC-019/AC1», y esa
  correlación existe.

### Qué se hizo

**Tabla `audit_log`** (`app/models/audit_log.py`) + migración `0003_audit_log`, con
las cuatro preguntas de AC4: **quién** (`actor_id`, `actor_role`,
`actor_email_masked`), **qué** (`action`, `target_type`, `target_id`, `detail`),
**cuándo** (`created_at`) y **desde dónde** (`ip`), más `request_id` para cruzar con
el log estructurado de T5.1.

**Helper** `app/platform/audit.py` y **cinco acciones cableadas**: cambio de rol,
publicación de artículo, borrado de documento RAG, login fallido y bloqueo de
cuenta.

**Endpoint de consulta** `GET /api/v1/audit`, solo administradores, con filtros
(`action`, `actor_id`, `target_id`, `since`, `until`), orden y paginación.

### Decisiones documentadas

- **Sin clave ajena a `users`.** El actor se guarda como UUID suelto. Una FK con
  `ON DELETE SET NULL` borraría el rastro justo al eliminar la cuenta que hizo algo
  —el momento en que más falta hace— y con `CASCADE` se llevaría la fila entera. El
  UUID identifica sin arrastrar datos personales.
- **El correo va enmascarado** (`a***@dominio.com`), como ya hacían los logs de
  auth. En un login fallido el actor no está autenticado y lo único que hay es el
  correo tecleado, que puede ni existir: guardarlo entero convertiría la tabla en un
  listado de direcciones. Eso es lo que pide el «sin PII innecesaria» de AC4.
- **Dos modos de escritura, y la asimetría es deliberada.** Por defecto la fila
  viaja **en la transacción del llamante** (`session.add`, sin commit): así no queda
  registrada una acción que acabó revertida, ni se pierde el registro de una que sí
  se aplicó. Los caminos que terminan lanzando una excepción —login fallido, que
  acaba en `401`— no tienen commit al que engancharse, así que usan `commit=True`.
  Y ahí un fallo del propio registro **no puede convertir un 401 en un 500**: se
  captura y se deja en el log de errores. En el camino transaccional, en cambio, un
  fallo debe propagarse, porque rompería la atomicidad.
- **El borrado RAG audita con `commit=True`** aunque haya sesión: el borrado ya
  ocurrió en Qdrant y **no es reversible** desde la aplicación. Sin commit propio,
  un fallo posterior de la petición dejaría el documento borrado y sin rastro.
- **El endpoint es solo de administradores.** El log concentra quién hizo qué y
  desde qué IP: es justo lo que no debe quedar a la vista de cualquier usuario
  autenticado.
- **Y es de solo lectura.** No hay endpoint para borrar ni editar entradas: purgar
  es política de retención (**T6.5 / #179**) y debe ocurrir por un proceso
  deliberado, no por una llamada de la API. Hay test que fija el `405`.
- **`limit` tope 200.** Esta tabla solo crece; una consulta sin límite sería un
  problema el día que de verdad haga falta usarla.
- **Los helpers de auth se unifican**: `_client_ip` y `_mask_email` de `auth.py`
  ahora delegan en los del módulo de auditoría, para que el log y el audit log
  enmascaren y resuelvan la IP exactamente igual. Dos implementaciones del
  enmascarado acabarían divergiendo.

### Un test ajeno que hubo que arreglar, y por qué no era cosmético

Añadir la tabla rompió dos casos de `test_migrations.py`. El *fixture* de «base
anterior a Alembic» la construía con `create_all`, que refleja los modelos de
**hoy** —ya con `audit_log`—, así que la migración `0003` chocaba con una tabla que
ya existía.

El fallo era del test, no del código: una base pre-Alembic de verdad tiene el
esquema **del corte**, no el de hoy. Ahora se genera aplicando `0001_baseline` y
borrando el sello. Con el *fixture* anterior, ese test se habría roto con **cada**
migración futura, y siempre por un motivo falso.

(De paso: la fixture es síncrona a propósito. `command.upgrade` abre su propio
bucle con `asyncio.run`, que revienta dentro de un test `async`.)

### Test nuevo

`backend/tests/test_audit_log.py` (20 casos), de extremo a extremo —petición HTTP →
fila en la tabla— porque lo que hay que garantizar no es que el helper funcione,
sino que **los routers lo llamen**: un audit log al que se le olvida un endpoint es
peor que no tenerlo, porque genera confianza infundada.

- **Enmascarado**: cinco formas de correo, incluidas las degeneradas; la entrada
  nunca guarda el correo en claro; un `actor_id` ilegible no tumba la acción.
- **Las cinco acciones dejan rastro**, con actor, objetivo, detalle y `request_id`
  correlacionado (`X-Request-ID` entrante → fila).
- **El login fallido se registra aunque acabe en `401`**, y **la contraseña
  intentada no aparece en ninguna parte** del volcado de la entrada.
- **Borrado RAG**: registra cuando el borrado ocurre y **no** registra cuando falla
  — el log describe hechos, no intentos.
- **Consulta**: 403 para no administradores, 401/403 anónimo, filtros, paginación,
  `limit` excesivo rechazado con 422, y `405` en `POST`/`DELETE`.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_audit_log.py -q
# → 20 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 353 passed
python scripts/validate_specs.py   # → [OK]
```

### Definition of Done (AC4)

- [x] **AC4** — las acciones sensibles quedan registradas con quién, qué, cuándo y
  desde dónde, sin PII innecesaria, y el registro es consultable.
- [x] Tests que cubren el cambio, en verde (20 nuevos; 353 en la suite).
- [x] Migración Alembic versionada (`0003_audit_log`), sin DDL a mano.
- [x] Sin secretos ni PII en el diff.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

- **#179 (T6.5)** es ahora la última tarea sustancial de E6, y esta tabla es una de
  las que su política de retención tiene que cubrir: crece sin tope y guarda IPs.
- **No hay UI**: la consulta es por API. Si se quiere un panel de auditoría, es
  trabajo de E7.
- Quedan acciones sensibles fuera del alcance de AC4 que podrían auditarse más
  adelante (borrado de artículos, cambios de configuración del LLM). AC4 nombra
  cuatro; se han cableado cinco (el bloqueo va aparte del login fallido porque
  merece su propia alerta).
