# Tarea #164 — T3.2 Gestión de secretos fuera de git + rotación

## 2026-07-01 08:50 — Completada ✅

- **Rama:** `sec/164-secrets-out-of-git`
- **PR:** pendiente → `develop`
- **Spec/ADR:** ADR-0003 (línea base de seguridad e identidad); sin spec dedicada
  (issue del backlog de hardening E3, DoD genérico de `docs/governance/GOVERNANCE.md §6`)
- **Dependencias:** ninguna

### Qué se hizo
Se sacaron de git los secretos hardcodeados y se endureció la validación de
`SECRET_KEY` para que un placeholder débil commiteado no pase como válido en
producción:

- **`docker-compose.yml`**: los secretos se inyectan por entorno con guardas
  fail-fast, siguiendo el patrón `"${VAR:?mensaje}"` ya usado para `QDRANT_API_KEY`:
  - `postgres.POSTGRES_PASSWORD` → `"${POSTGRES_PASSWORD:?...}"` (antes `password`).
  - `backend.DATABASE_URL` se **deriva** de `POSTGRES_PASSWORD`
    (`postgresql+asyncpg://postgres:${POSTGRES_PASSWORD:?...}@postgres:5432/alejandria`),
    sin contraseña inline.
  - `backend.SECRET_KEY` → `"${SECRET_KEY:?...}"` (antes
    `local-dev-secret-key-change-in-production`).
  - **No** se tocaron Qdrant, Ollama ni los `ports:` (eso es #163, va en otra PR).
- **`backend/app/core/config.py`**: `_validate_settings` ahora rechaza en
  producción (`DEBUG=false`) cualquier `SECRET_KEY` vacía, de longitud < 32, o que
  contenga marcadores de placeholder (`change-in-production`, `changeme`,
  `cambia-esto`, `dev-secret`, `your-secret-key`, `password`, …). Se conserva el
  fail-fast con `ValueError` y un mensaje claro que indica `openssl rand -hex 32`.
  Helper reutilizable `_is_insecure_secret_key`. En `DEBUG=true` no se exige clave
  fuerte (conveniencia de dev/CI); el `SECRET_KEY=ci-secret-not-for-prod` de los
  tests sigue funcionando.
- **`.env.example` (raíz y `backend/`)**: reescritos con los secretos vacíos
  (`SECRET_KEY=`, `POSTGRES_PASSWORD=`, `REDIS_PASSWORD=`, `QDRANT_API_KEY=`,
  `MINIO_ROOT_*=`), comentarios de generación (`openssl rand -hex 32/24`) y una
  cabecera de rotación. Se eliminaron los valores `password` y `minioadmin`.
- **Docs de rotación**: `SECURITY.md` gana la sección «Gestión y rotación de
  secretos» (generación, guardas de compose, validación fail-fast y procedimiento
  de rotación). `docs/adr/0003-*.md` gana una nota de implementación de T3.2.
- **Tests**: `backend/tests/test_config_secret_validation.py` (24 casos):
  - claves débiles/placeholder/cortas → `ValueError` con `DEBUG=false`;
  - las mismas claves toleradas con `DEBUG=true`;
  - clave fuerte (64 hex) aceptada; `ci-secret-not-for-prod` OK en debug;
  - escaneo de `docker-compose.yml`: falla si reaparecen literales
    (`POSTGRES_PASSWORD: password`, `postgres:password@`, `minioadmin`,
    `:password@`, el placeholder de `SECRET_KEY`) y exige que `SECRET_KEY` y
    `POSTGRES_PASSWORD` estén inyectados con guarda `${VAR:?...}`.

### Definition of Done
- [x] Criterios aplicables (gobernanza §6) — control de infra/identidad de ADR-0003
  (secretos fuera de git, validación fail-fast); sin spec dedicada.
- [x] Secretos fuera de git — compose usa `${VAR:?...}`; `.env.example` sin valores
  reales; `.env` ya está en `.gitignore`.
- [x] Rotación soportada y documentada — secretos por entorno; procedimiento en
  `SECURITY.md` (cambiar env + `--force-recreate`).
- [x] Placeholder débil no pasa en producción — `_validate_settings` rechaza el
  valor de compose y otros placeholders/longitud insuficiente cuando `DEBUG=false`.
- [x] Tests automatizados que cubren el cambio (verdes) — 24 nuevos; suite backend
  completa en verde (49 passed).
- [x] Sin secretos ni PII en el diff — solo `${VARIABLES}` y placeholders vacíos.
- [x] Docs/ADR actualizados — `SECURITY.md`, ADR-0003, ambos `.env.example`.

### Verificación
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_config_secret_validation.py -q`
  → `24 passed`.
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q`
  → `49 passed` (sin regresiones).
- `python scripts/validate_specs.py` → `[OK] Specs SDD validas.`
- `docker compose config` **sin** variables → falla:
  `required variable POSTGRES_PASSWORD is missing a value` / `SECRET_KEY is missing`.
- `SECRET_KEY=x POSTGRES_PASSWORD=x QDRANT_API_KEY=x docker compose config` → OK (exit 0).
- Import con `DEBUG=false` + placeholder de compose → `ValueError` (abort); con
  `DEBUG=false` + `openssl rand -hex 32` → import OK.

### Fuera de alcance / notas
- No se tocaron los `ports:` ni la config de Qdrant/Ollama: esa remediación es la
  tarea hermana #163 (PR aparte). El único fichero compartido es
  `docker-compose.yml` — posible conflicto de merge trivial con la PR de #163
  (secciones distintas: #164 toca `postgres.environment` y `backend.environment`;
  #163 toca `ports:`/Qdrant).
- El repo actual **no** tiene servicios `redis` ni `minio` en `docker-compose.yml`
  (sí variables en config/.env.example). Se dejaron `REDIS_PASSWORD`/`MINIO_*` como
  placeholders vacíos en `.env.example` para cuando se añadan esos servicios; no
  hay literal que sacar del compose porque no existe el servicio.
- `backend/config.yaml` y `config.yaml` mantienen `secret_key:
  CAMBIA-ESTO-EN-PRODUCCION-...` (placeholder, no secreto real): la nueva
  validación lo rechaza en producción, que es el comportamiento deseado.
- La verificación de compose se hizo con `docker compose config` (interpolación y
  guardas); no se levantaron servicios en este entorno.
