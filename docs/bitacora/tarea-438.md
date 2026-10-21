# Tarea #438 — T20.6 Migración y modelos: informe, estado requires_human_review, aprobación y autor responsable; API del informe

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-6-migracion-informe-aprobacion`
- **PR:** la de esta rama → `develop` (`Closes #438`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC6 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.4 (#436, ya en `develop`)

### Dónde estaba el problema

La compuerta (T20.4) producía un informe en memoria y nada lo guardaba: no había dónde persistirlo,
ni estado para «requiere revisión humana», ni campos para la aprobación explícita o el autor
responsable. Sin esto no se puede reevaluar, ni auditar qué se aprobó, ni ligar la aprobación a un texto.

### Qué se hizo y por qué

- **Migración `0006_publication_gate`** (con test de paridad `create_all`/migraciones en verde):
  - tabla `publication_gate_reports` (`article_id` CASCADE, `run_id` SET NULL, `text_sha256`, `criteria`,
    `sources`, `created_by`, `created_at`, índices);
  - `articles.responsible_author_id`, `approved_by`, `approved_at`, `approved_text_sha256`, todas nulas:
    los artículos existentes —también los ya publicados— no se tocan;
  - `ArticleStatus.REQUIRES_HUMAN_REVIEW`. En Postgres es `ALTER TYPE … ADD VALUE IF NOT EXISTS` fuera
    de transacción (la etiqueta es el **nombre** del miembro, como el resto de `articlestatus`); en SQLite
    no hay nada que añadir. El `downgrade` no puede quitar la etiqueta de Postgres (se deja, es inocua).
- **`publication_gate/service.py`:** `text_sha256`, `latest_report`, `is_current` (el informe vigente es el
  último cuya huella coincide con el cuerpo) y `evaluate_and_store`. Cada evaluación inserta una fila
  **nueva**: no sobrescribe.
- **API** (`routers/articles.py`), accesible para autor, revisor asignado o admin, 403 al resto:
  - `GET /api/v1/articles/{id}/gate-report` → `{report, current}`; `report: null` si el artículo no tiene
    informe (anteriores a esta spec: «sin informe»).
  - `POST /api/v1/articles/{id}/gate-report` → reevalúa el texto actual con las fuentes del último informe.
    No recibe ningún informe: lo escribe solo el backend.
- **Decisión: sin fuentes estructuradas, referencias `not_verified`.** Un manuscrito cuyo informe no tiene
  fuentes (p. ej. un artículo antiguo reevaluado) no se aprueba por ausencia de referencias: se cierra
  así CHK034 en el sentido conservador de ADR-0011.
- `ArticleResponse` expone `responsible_author_id`, `approved_by` y `approved_at` (nulos por defecto).
- `docs/governance/data-retention.md`: se documenta la tabla nueva y, con honestidad, que **hoy no caduca**;
  la política objetivo (`RETENTION_GATE_REPORTS_DAYS`) la implementa T20.13 (#445).

### Definition of Done

- [x] **AC6** — informe con estado y evidencia por criterio, huella del texto, fecha y ejecución; legible
  por API; nueva evaluación = otra fila; reevaluar; informe vigente por huella; «sin informe» para los antiguos.
- [x] Tests: `backend/tests/test_gate_report_api.py` (9), migraciones y retención en verde. Suite: 1190
  pasados; los mismos 4 fallos que `develop` (`test_no_tracked_databases` es un bloqueo de archivo de
  Windows al limpiar, ya fallaba sin estos cambios).
- [ ] Nada **usa** aún el estado nuevo ni los campos de aprobación: T20.8 (3 vueltas), T20.9 (bloqueantes),
  T20.10 (aprobación) y T20.11 (`can_publish`).
- [ ] El Publicador todavía no guarda el informe tras el Formateador (llega con T20.9).
- [ ] Frontend: el valor `requires_human_review` aún no se muestra (T20.14).

### Verificación

Migración probada en SQLite (paridad con `create_all`). **No se ha ejecutado contra Postgres:** el
`ADD VALUE` y las claves ajenas con nombre están escritos según el patrón de `0002`, pero conviene un
`alembic upgrade head` en una base Postgres antes de desplegar.

### Fuera de alcance / notas

- La reevaluación por API depende de las fuentes del último informe; para una primera evaluación de un
  artículo sin informe llamará al pipeline (T20.9), no a este endpoint.
- El proyecto de la compuerta es el de AlejandrIA (`alejandria.package().gate`), igual que `GET /flows/rules`.
