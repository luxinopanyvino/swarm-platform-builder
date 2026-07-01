# Tarea #163 — T3.1 Autenticar Qdrant (API key) y no exponer puertos internos

## 2026-07-01 — Completada ✅

- **Rama:** `sec/163-qdrant-auth-internal-ports`
- **PR:** pendiente (a abrir contra `develop` con `Closes #163`)
- **Spec/ADR:** ADR-0003 (línea base de infraestructura/seguridad); Épica E3.
  Sin spec dedicada (DoD genérico, `docs/governance/GOVERNANCE.md §6`)
- **Dependencias:** ninguna

### Problema
Qdrant (`:6333/:6334`), Ollama (`:11434`) y Postgres (`:5432`) se publicaban al
host en `docker-compose.yml`, y Qdrant no exigía autenticación. Un servicio
interno accesible sin auth es explotable (incl. vía SSRF, ya mitigada en #159).

### Qué se hizo
- **Autenticación de Qdrant en todas las llamadas del backend**:
  - Nuevo `backend/app/shared/qdrant.py` con `qdrant_headers(api_key=None)` (cabecera
    `api-key` cuando hay clave) y `qdrant_client()` (construye el `httpx.AsyncClient`
    con esa cabecera y `base_url`).
  - Se taparon las dos rutas que pegaban a Qdrant **sin** cabecera de auth:
    `backend/app/routers/ai.py` (`_ensure_qdrant_collection`, `ingest`) y
    `backend/app/modules/ai/adapters/http.py` (`ingest_source`, `assist`) — ahora
    usan `qdrant_client()`.
  - La capa RAG (`rag.py`) ya enviaba la cabecera `api-key` (patrón inline en ~15
    sitios); se deja intacta (ya autenticada) para no arriesgar sus imports
    perezosos anti-ciclos. El helper centraliza los puntos que faltaban.
- **`docker-compose.yml` — no exponer puertos internos + auth**:
  - `qdrant`: `QDRANT__SERVICE__API_KEY` desde el entorno; **sin** `ports:`.
  - `ollama` y `postgres`: **sin** `ports:` (solo red interna `alejandria_network`).
  - `backend`: `QDRANT_API_KEY` desde el entorno (debe coincidir con el de qdrant).
  - Publicados solo `backend:8000` y `frontend:8080` (superficie de la app).
  - `QDRANT_API_KEY` se inyecta con `${QDRANT_API_KEY:?...}`: `docker compose`
    **falla en arranque** si no se define (nunca se commitea un valor).
- **Docs**: `.env.example` (raíz y `backend/`) documentan `QDRANT_API_KEY` como
  obligatoria en despliegue.

### Definition of Done
- [x] Qdrant autenticado: todas las llamadas del backend envían `api-key` cuando
  la clave está configurada.
- [x] Puertos de servicios internos (qdrant/ollama/postgres) no publicados al host.
- [x] Tests automatizados que cubren el cambio (verdes) — 5 nuevos; suite completa
  del backend en verde (30 passed).
- [x] Sin secretos ni PII en el diff (la clave se inyecta por entorno).
- [x] Documentación — `.env.example` y esta bitácora.

### Verificación
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_qdrant_auth.py -q` → `5 passed`.
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q` → `30 passed` (sin regresiones).
- `QDRANT_API_KEY=dummy docker compose config` → OK; solo `8000`/`8080` publicados;
  `QDRANT__SERVICE__API_KEY` == `QDRANT_API_KEY`.
- `docker compose config` sin la variable → **falla** (guard `:?`), como se espera.
- `python scripts/validate_specs.py` → OK.

### Fuera de alcance / notas
- Sin Docker/Qdrant vivo en el contenedor de CI/dev, la verificación end-to-end del
  runtime de Qdrant es parcial; se cubre el lado cliente con tests y el compose con
  `docker compose config`.
- No se refactorizó el patrón inline de `rag.py` (ya correcto) para no tocar sus
  imports perezosos anti-ciclos; el helper queda disponible para futuros usos.
- La gestión general de secretos (Postgres/Redis/MinIO, rotación) es la tarea
  hermana **T3.2 (#164)**, aparte.
