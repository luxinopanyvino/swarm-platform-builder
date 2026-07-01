# Tarea #156 — T1.4 Sacar el token JWT del query string del SSE

## 2026-07-01 — Completada ✅

- **Rama:** `sec/156-sse-stream-ticket`
- **PR:** pendiente (a abrir contra `develop` con `Closes #156`)
- **Spec/ADR:** ADR-0003 (línea base de identidad); Épica E1. Sin spec dedicada
  (issue de DoD genérico, `docs/governance/GOVERNANCE.md §6`)
- **Dependencias:** ninguna

### Problema
El stream SSE (`GET /api/v1/agents/{id}/stream`) se autenticaba con el JWT en el
query string (`?token=<JWT>`). Un token de acceso de larga vida en la URL se
filtra por logs de servidor, historial del navegador y logs de proxy.

### Qué se hizo
Se sustituyó el JWT en la URL por un **ticket efímero de un solo uso** (el
`EventSource` del navegador no puede enviar cabecera `Authorization`):

- **Nuevo `backend/app/core/stream_auth.py`**: store en proceso de tickets
  opacos (`secrets.token_urlsafe`), ligados a `(user_id, article_id)`, con TTL
  corto y **un solo uso** (`consume_ticket` los elimina en cualquier intento,
  evitando replay). Incluye `reset_stream_tickets()` para tests.
- **`backend/app/routers/agents.py`**:
  - Nuevo `POST /api/v1/agents/{article_id}/stream-ticket` (autenticado por
    Bearer vía `get_current_user`, verifica propiedad del artículo) que emite el
    ticket.
  - `GET /{article_id}/stream` ahora recibe `?ticket=` en vez de `?token=`, lo
    **consume** y valida propiedad; ya no usa `verify_token`. Sin ticket válido
    → `401`.
- **Config**: `SSE_TICKET_TTL_SECONDS` (por defecto 30 s) en `Settings` /
  `_build_settings` (`security.sse_ticket_ttl_seconds`).
- **Frontend**:
  - `frontend/src/api/agents.js`: nuevo `getStreamTicket(articleId)` (POST
    autenticado) y `getStreamUrl(articleId, ticket)` con `?ticket=`.
  - `frontend/src/pages/ExecutionPage.jsx`: el `useEffect` del SSE pide primero
    el ticket y luego abre el `EventSource`; ya no lee el JWT de `localStorage`
    para la URL. Limpieza con flag `cancelled` + cierre del `EventSource`.

### Definition of Done
- [x] El JWT ya no viaja en el query string del SSE; autenticación por ticket de
  un solo uso y corta vida.
- [x] Tests automatizados que cubren el cambio (verdes) — 9 nuevos (store +
  endpoints); suite completa del backend en verde (34 passed).
- [x] `npm run build` y `npm run build:public` compilan.
- [x] Sin secretos ni PII en el diff.
- [x] Documentación — esta bitácora.

### Verificación
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_sse_stream_ticket.py -q` → `9 passed`.
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q` → `34 passed` (sin regresiones).
- `cd frontend && npm run build && npm run build:public` → ambos OK.

### Fuera de alcance / notas
- El store de tickets es **en proceso** (como `active_streams`). Un despliegue
  multi-worker debería respaldarlo con Redis — seguimiento en T4.3 (#170).
- Revocación de JWT / refresh (jti) es la tarea hermana **T1.3 (#155)**, aparte.
