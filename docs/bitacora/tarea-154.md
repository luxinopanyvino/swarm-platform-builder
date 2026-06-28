# Tarea #154 — T1.2 Rate limiting + bloqueo de cuenta en login/register

## 2026-06-28 17:11 — Completada ✅

- **Rama:** `sec/154-rate-limit-account-lockout`
- **PR:** #213 → `develop`
- **Spec/ADR:** ADR-0003 (línea base de seguridad e identidad); sin spec dedicada
  (issue sembrado por bootstrap, DoD genérico de `docs/governance/GOVERNANCE.md §6`)
- **Dependencias:** ninguna (#153 ya mergeada/cerrada)

### Qué se hizo
Se añadió protección anti fuerza bruta / credential stuffing a los endpoints de
autenticación (`/api/v1/auth/login` y `/api/v1/auth/register`):

- Nuevo módulo `backend/app/core/rate_limit.py` con dos controles
  complementarios, sin dependencias externas (estado en proceso):
  - `SlidingWindowCounter`: rate limiting por IP en ventana deslizante.
  - `AccountLockoutTracker`: bloqueo temporal de cuenta tras N fallos de login
    consecutivos (defensa frente a stuffing distribuido contra una cuenta).
- `backend/app/routers/auth.py`:
  - `register` aplica rate limit por IP → `429` con `Retry-After`.
  - `login` aplica (1) rate limit por IP → `429`, (2) rechazo temprano si la
    cuenta está bloqueada → `423` con `Retry-After`, (3) registro de fallo y
    bloqueo al superar el umbral; un login correcto resetea el contador.
  - Helper de IP con soporte de `X-Forwarded-For` (primer salto).
- Observabilidad: logs `WARNING/INFO` en `app.auth` para rate-limit excedido,
  bloqueo activado y acceso a cuenta bloqueada. El email se enmascara
  (`_mask_email`) para no registrar PII; nunca se loguea la contraseña.
- Configuración: nuevas claves en `Settings`/`_build_settings`
  (`AUTH_RATELIMIT_MAX_ATTEMPTS`, `AUTH_RATELIMIT_WINDOW_SECONDS`,
  `AUTH_LOCKOUT_MAX_FAILED`, `AUTH_LOCKOUT_SECONDS`), documentadas en los dos
  `config.yaml`. Cada control se desactiva con su `max = 0`.
- Tests: `backend/tests/test_auth_rate_limit_lockout.py` (unitarios de las
  primitivas + e2e de los endpoints) y `backend/tests/conftest.py` con fixture
  autouse que resetea el estado de throttling entre tests (evita acoplamiento
  por el singleton de proceso y mantiene verdes las suites existentes).

### Definition of Done
- [x] Cumple criterios aplicables (gobernanza §6) — control de identidad de la
  línea base ADR-0003; sin spec dedicada que añadir.
- [x] Rate limiting + bloqueo de cuenta en login y register — implementado en
  `auth.py` con `429` (rate limit) y `423` (cuenta bloqueada).
- [x] Tests automatizados que cubren el cambio (verdes) — 8 nuevos tests; suite
  completa del backend en verde (25 passed).
- [x] Sin secretos ni PII en el diff — emails enmascarados en logs; sin
  contraseñas ni secretos; `.db` no commiteados.
- [x] Documentación actualizada — comentarios en `config.yaml` (raíz y backend)
  y esta bitácora.
- [x] Observabilidad añadida — logs estructurados de eventos de throttling/bloqueo.

### Verificación
- `cd backend && DEBUG=true python -m pytest tests/test_auth_rate_limit_lockout.py -q`
  → `8 passed`.
- `cd backend && DEBUG=true python -m pytest -q` → `25 passed` (sin regresiones).

### Fuera de alcance / notas
- El estado de throttling es **en proceso** (sin Redis). Suficiente para
  un worker / dev / CI; un despliegue multi-worker debería respaldarlo con un
  almacén compartido (Redis). Documentado en el docstring del módulo como
  seguimiento.
- El bloqueo de cuenta vive en memoria (no persiste reinicios) para evitar una
  migración de esquema (el proyecto usa `create_all`, sin Alembic ejecutado).
- No se tocó el módulo `app/modules/auth` (no es el router activo; `main.py`
  monta `app.routers.auth`).
