# Tarea #153 — T1.1 Rol seguro por defecto en el registro

## 2026-06-28 12:25 — Completada ✅

- **Rama:** `sec/t1.1-default-signup-role`
- **PR:** #pendiente → `develop`
- **Spec/ADR:** [SPEC-001](../specs/SPEC-001-secure-registration-rbac.md) (Épica E1) · ADR-0003
- **Dependencias:** ninguna

### Qué se hizo
Se aplica el principio de mínimo privilegio al registro y se endurecen los
controles de acceso asociados:

- `register()` deja de heredar el default `REDACTOR` y fija explícitamente el rol
  a partir de `settings.DEFAULT_SIGNUP_ROLE` mediante el helper
  `resolve_default_signup_role()`, que solo acepta `lector`/`publico` y, ante
  cualquier valor inválido o ausente, hace fallback seguro a `LECTOR`.
- Defensa en profundidad: el default de la columna `UserModel.role` pasa de
  `REDACTOR` a `LECTOR`.
- Nueva dependencia `require_redactor` (en `auth.py`) que exige rol
  `REDACTOR`/`ADMIN`; se aplica a los endpoints que ejecutan/crean recursos
  privilegiados: ejecución de pipeline (`POST /agents/{article_id}/run`, que
  conduce internamente al scraper del investigador), subida RAG por agente
  (`POST /agents/{agent_name}/rag/upload`) y subida a la biblioteca RAG global
  (`POST /agents/rag/library/upload`). Los roles mínimos reciben 403.
- Fail-safe de configuración: el merge de `ENABLE_DEV_ROLE_PROMOTION` ahora usa
  default `False` cuando la clave está ausente (antes `True`). Se añade el ajuste
  `DEFAULT_SIGNUP_ROLE` (default `lector`).
- Se documentan ambas variables en `.env.example` (raíz y backend) y se ajusta
  `config.yaml` (raíz y backend) a valores seguros por defecto.
- Tests nuevos en `tests/test_secure_registration_rbac.py` cubriendo AC1–AC3.

### Definition of Done
- [x] **AC1** — El registro asigna `LECTOR` (mínimo privilegio, configurable a
  `publico`); un usuario recién registrado recibe 403 al ejecutar pipeline, subir
  RAG por agente, subir a la biblioteca RAG y, transitivamente, invocar el
  scraper (gobernado por `require_redactor`). Cubierto por
  `test_register_assigns_minimal_privilege_role` y
  `test_fresh_user_cannot_run_pipeline_upload_rag_or_scrape`.
- [x] **AC2** — Un no-admin que intenta cambiar un rol vía
  `PUT /auth/users/{id}/role` recibe 403 (`require_admin`); solo `ADMIN` puede.
  Cubierto por `test_non_admin_cannot_change_role` y `test_admin_can_change_role`.
- [x] **AC3** — `ENABLE_DEV_ROLE_PROMOTION` sin configurar resuelve a `False`
  (fix del merge en `config.py`) y `POST /auth/dev/promote-reviewer` responde 403.
  Cubierto por `test_dev_promote_reviewer_is_forbidden_by_default` y
  `test_enable_dev_role_promotion_failsafe_when_unset`.
- [x] **AC4** — Existen tests automatizados para AC1–AC3 en
  `backend/tests/test_secure_registration_rbac.py`.

### Verificación
- `cd backend && python -m pytest tests/test_secure_registration_rbac.py -q` → 6 passed
- `cd backend && python -m pytest -q` → 17 passed (sin regresiones)

### Fuera de alcance / notas
- No hay endpoint de scraper expuesto de forma directa: se invoca dentro del
  pipeline del investigador, por lo que el guard sobre `POST /{article_id}/run`
  lo cubre transitivamente.
- No se incluye script de migración/revisión de roles para usuarios existentes
  con rol amplio (SPEC-001 §5, riesgo de seguimiento) ni el log de auditoría de
  cambios de rol (épica E6); quedan fuera del alcance de T1.1.
- `config.yaml` versionado se fija a `enable_dev_role_promotion: false`; el atajo
  de dev debe activarse explícitamente solo en local.
