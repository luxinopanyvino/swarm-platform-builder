# Tarea #442 — T20.10 Aprobación humana explícita con registro de usuario, decisión, fecha y versión

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-10-aprobacion-humana`
- **PR:** la de esta rama → `develop` (`Closes #442`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC8 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.6 (#438, ya en `develop`)

### Dónde estaba el problema

`POST /articles/{id}/approve` publicaba si quien llamaba era admin o revisor asignado: no miraba la
compuerta, no distinguía al propietario del artículo, no guardaba qué texto se aprobó y no dejaba
más rastro que el cambio de estado. Un administrador que era además el autor se aprobaba a sí mismo.

### Qué se hizo y por qué

- `platform/publication_gate/approval.py` (nuevo): `approval_denial(...)`, una función pura con las
  reglas de AC8, para que `approve` y —en T20.11— `publish` apliquen exactamente las mismas.
  - **403 (quién):** solo el revisor asignado o un administrador, y **nunca el propietario** del
    artículo (quien lanzó el pipeline), tampoco si es admin o revisor asignado.
  - **409 (qué):** sin autor responsable declarado (`no_responsible_author`), sin informe
    (`no_gate_report`), informe de otro texto (`text_changed`) o con bloqueantes (`gate_blockers`).
    El detalle del 409 es `{code, message}` para que el frontend (T20.14) pueda distinguirlos.
- `routers/articles.py` (`approve`): aplica esas reglas y registra `approved_by`, `approved_at` y
  `approved_text_sha256` (huella del texto aprobado); deja una fila de auditoría `article.approved` con
  la decisión, la huella y, si la compuerta estaba en modo aviso, qué no se cumplía.
- Nuevo `PUT /articles/{id}/responsible-author` (autor del artículo o admin; el destino debe ser un
  usuario activo): sin él AC8 no se podría cumplir, porque nada declaraba al autor responsable.
- Ajustes: `PUBLICATION_GATE_ENFORCE` (por defecto `true`; con `false` los problemas de compuerta se
  registran y avisan pero no bloquean, y la aprobación humana sigue siendo obligatoria) y
  `PUBLICATION_ALLOW_SELF_APPROVAL` (autoaprobación para un solo usuario), **imposible de encender con
  `DEBUG=false`**: está en `_DEV_ONLY_FLAGS`, que lo apaga venga de donde venga.

### Definition of Done

- [x] **AC8 (parte de la aprobación)** — usuario, decisión, fecha y huella registrados; 409 por texto
  cambiado, bloqueantes o falta de autor responsable; 403 al propietario y a quien no es revisor/admin;
  autoaprobación solo en desarrollo.
- [x] Tests: `backend/tests/test_approval.py` (17). Suite: 1207 pasados, los mismos 4 fallos que `develop`.
- [ ] «El Publicador deja el artículo en `in_review` y nunca `published`» (otra mitad de AC8): T20.9/T20.11.
- [ ] `publish` directo sigue sin aplicar estas reglas hasta T20.11.

### Verificación

Pruebas de API con SQLite y un informe de compuerta insertado a mano; no se ejecutó el pipeline completo.

### Fuera de alcance / notas

- **Cambio de comportamiento visible:** con la compuerta en vigor, `approve` devuelve 409 a cualquier
  artículo sin informe vigente o sin autor responsable, y un admin que es el autor ya no puede aprobar el
  suyo. Para desplegar sobre datos existentes, empezar con `PUBLICATION_GATE_ENFORCE=false` (AC16).
- La «decisión» se registra como `approved` en la auditoría; el rechazo sigue en `reject`
  (`rejection_comment`). No hay columna propia de decisión.
- Abiertos del checklist: aprobaciones concurrentes y aprobación con la compuerta caducada más allá del
  409 por huella (CHK030), y quién rellena el autor responsable por defecto (CHK015).
