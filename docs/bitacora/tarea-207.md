# Tarea #207 — T8.1 Consolidar config/database, partir models.py y unificar HTTP

## 2026-07-03 22:39 — Completada ✅

- **Rama:** `chore/207-consolidate-config-db-split-models`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #207`)
- **Spec/ADR:** SPEC-013 (Refactor estructural e independencia de proyectos),
  Épica E8, ADR-0005. Criterios vinculantes de T8.1: **AC1** y **AC2**.
- **Dependencias:** ninguna (`depends_on: []`).

### Qué se hizo
Refactor mecánico **sin cambio funcional**: se consolidaron los módulos de
configuración y base de datos bajo `core/` y se partió el monolito
`app/models.py` en un paquete por dominio.

**AC1 — config y database únicos bajo `core/`:**
- `git mv backend/app/shared/database.py → backend/app/core/database.py` (sin
  tocar su lógica; sigue importando `from app.core.config import settings`).
- Eliminados los *shims* legacy `backend/app/config.py` y `backend/app/database.py`.
- Actualizadas **todas** las importaciones del código y de los tests a los
  módulos canónicos:
  - `from app.database import …` → `from app.core.database import …`
  - `from app.shared.database import …` → `from app.core.database import …`
  - No quedaba ningún `from app.config import …` (solo el shim, ya eliminado).
- Config: `app/core/config.py` ya era el módulo bueno; el shim `app/config.py` se
  retiró. Único módulo de config y único de base de datos, ambos bajo `core/`.

**AC2 — `app/models.py` monolítico partido en paquete:**
- `backend/app/models.py` (507 líneas) convertido en el paquete
  `backend/app/models/` con submódulos por dominio:
  - `enums.py` (UserRole, ArticleStatus, ProjectUseCaseType, ScientificFormat)
  - `user.py` (UserModel + DTOs de auth + TokenResponse)
  - `article.py` (ArticleModel + AuthorDTO + DTOs de artículo)
  - `project.py` (ProjectModel + UserProjectAccessModel + DTOs)
  - `agent_profile.py` (AgentProfileModel + AgentProfileResponse)
  - `agent_run.py` (AgentRunModel + DTOs de run)
  - `saved_flow.py` (SavedFlowModel + DTOs)
  - `checkpoint.py` (FlowCheckpointModel + DTOs)
  - `notification.py` (NotificationModel + NotificationResponse)
  - `ai.py` (DTOs de AI assist/ingest/format, sin ORM)
- `__init__.py` importa todos los submódulos y **re-exporta** todos los nombres
  públicos, preservando la superficie `from app.models import X` (los ~13 sitios
  consumidores no cambian). Cada ORM importa `Base` desde `app.core.database`, de
  modo que todos los modelos se registran en `Base.metadata` (verificado: mismas
  9 tablas que antes).

**"Unificar HTTP" (título) — fuera de alcance en esta PR:** SPEC-013 §4 lo cita
como objetivo general (E8) pero los criterios vinculantes de T8.1 son solo AC1 y
AC2. Consolidar el patrón HTTP implicaría tocar routers/adaptadores (`modules/*/
adapters/http.py`) y lógica de negocio, con riesgo funcional fuera de un refactor
mecánico. Se difiere a una tarea/PR posterior de E8. No se amplió el alcance.

### Definition of Done (AC1/AC2)
- [x] **AC1** — Un único módulo de config (`app/core/config.py`) y uno de base de
  datos (`app/core/database.py`) bajo `core/`; ya no existen `app/config.py`,
  `app/database.py` ni `app/shared/database.py`; la app arranca
  (`import app.main` OK).
- [x] **AC2** — `app/models.py` monolítico ya no existe; cada modelo vive en su
  submódulo bajo `app/models/`; los tests existentes siguen pasando (63 passed).
- [x] Sin secretos ni PII en el diff; no se commiteó ningún `.db` ni artefactos.
- [x] Specs válidas (`scripts/validate_specs.py` OK); AC1/AC2 marcados `[x]` en
  SPEC-013.

### Verificación (comandos ejecutados)
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q`
  → **63 passed** (sin regresiones).
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -c "import app.main"`
  → importa sin error (app arranca).
- Igualdad de tablas registradas antes/después:
  `['agent_profiles','agent_runs','articles','flow_checkpoints','notifications','projects','saved_flows','user_project_access','users']`
  → idéntico (9 tablas).
- `grep -rn "app.config import|app.database import|app.shared.database" backend/app backend/tests`
  → sin coincidencias.
- `ls backend/app/models.py` → no existe (ahora es paquete `backend/app/models/`).
- `python scripts/validate_specs.py` → `[OK] Specs SDD validas.`

### Fuera de alcance / notas
- "Unificar HTTP" se difiere (ver arriba): toca routers/lógica, no es mecánico y
  no está en AC1/AC2.
- Warning preexistente de SQLAlchemy al hacer DROP por FK circular
  `projects↔users` (no relacionado con este cambio; ya existía).
- Posible conflicto de merge previsible con PRs en vuelo que toquen imports de
  `app.models`/`app.database`/`app.shared.database` (p. ej. #229): al ser un
  refactor de imports transversal, resolver rebaseando sobre `develop`.
