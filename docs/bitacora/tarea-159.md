# Tarea #159 — T2.1 Protección SSRF en el scraper + quitar `verify=False`

## 2026-07-01 — Completada ✅

- **Rama:** `claude/github-project-tasks-q9ktn1`
- **PR:** pendiente (a abrir contra `develop` con `Closes #159`)
- **Spec/ADR:** [SPEC-002](../specs/SPEC-002-scraper-ssrf-protection.md) · ADR-0003 · Épica E2 (AppSec)
- **Dependencias:** ninguna

### Qué se hizo
Se protegió el scraper del Investigador frente a SSRF y se restauró la
verificación TLS, centralizando el control de *egress* saliente:

- **Nuevo módulo `backend/app/shared/egress.py`** — guarda central de egress:
  - `assert_safe_url(url)` / `is_egress_allowed(url)`: exige esquema `http(s)`,
    resuelve el host con `socket.getaddrinfo` y **rechaza toda IP no pública**
    (`is_private/is_loopback/is_link_local/is_reserved/is_multicast/is_unspecified`),
    cubriendo IPv4, IPv6 e IPv4-mapped (`::ffff:127.0.0.1`). Valida **todas** las
    IPs resueltas (anti DNS-rebinding, AC2) y loguea el bloqueo (AC1).
  - Excepción propia `EgressBlocked(url, reason)`, contador `blocked_total()` y
    caché corta de resolución (TTL 30 s) para amortizar el coste DNS por scrape.
  - Allowlist configurable por dominio + subdominios (`SCRAPER_ALLOWED_DOMAINS`);
    vacía = cualquier host público (AC4).
- **`scraper.py`**: se invoca `assert_safe_url` en `_fetch_page` **antes** de
  cualquier petición y `is_egress_allowed` antes de descargar `robots.txt`; se
  quitó `verify=False` de las 5 llamadas httpx y se puso `ignore_https_errors=False`
  en el contexto de Playwright (AC3).
- **`tools.py`**: se quitó `verify=False` de las 2 llamadas httpx de búsqueda
  (arXiv/Wikipedia) — TLS activo (AC3).
- **Config**: nueva clave `SCRAPER_ALLOWED_DOMAINS` en `Settings`/`_build_settings`
  (soporta override por env como lista separada por comas y `config.yaml`
  `agents.investigador.allowed_domains`), documentada en ambos `.env.example`.
- **Tests**: `backend/tests/test_scraper_ssrf.py` (21 casos) mockeando
  `getaddrinfo`: bloqueo de loopback/privadas/link-local/IPv6/metadata, host
  público permitido, fallo DNS, esquemas no-http, allowlist, integración de que
  el scraper rechaza `127.0.0.1:6333` y `169.254.169.254` sin tocar la red, y
  regresión TLS (ningún módulo saliente contiene `verify=False`).

### Definition of Done
- [x] Criterios de aceptación SPEC-002 (AC1–AC5) cumplidos y marcados en la spec.
- [x] Tests automatizados que cubren el cambio (verdes) — 21 nuevos; suite
  completa del backend en verde (46 passed).
- [x] Sin secretos ni PII en el diff.
- [x] Documentación actualizada — SPEC-002, `.env.example` (raíz y backend) y
  esta bitácora.
- [x] Observabilidad — log `WARNING` por URL bloqueada + contador `blocked_total()`.

### Verificación
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_scraper_ssrf.py -q` → `21 passed`.
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q` → `46 passed` (sin regresiones).

### Fuera de alcance / notas
- **Redirecciones**: `httpx` sigue redirects; la guarda valida la URL inicial,
  no cada salto. Un redirect a un host interno no se re-valida hoy. Mitigación
  futura: hook de egress por-redirect o `follow_redirects=False` en el scraper.
- El contador `blocked_total()` es en proceso; su exposición como métrica
  Prometheus corresponde a la tarea **T5.2 (#172)**.
- No se tocó `rag.py` (sus fetch van a Ollama/Qdrant configurados, no a URLs
  influidas por el usuario).
