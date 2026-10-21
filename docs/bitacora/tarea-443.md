# Tarea #443 — T20.11 Una sola puerta a published: can_publish y el endpoint publish directo

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-11-can-publish`
- **PR:** la de esta rama → `develop` (`Closes #443`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC10 y AC13 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.4 (#436), T20.7 (#439) y T20.10 (#442), ya en `develop`

### Dónde estaba el problema

Había **cuatro** sitios que asignaban `PUBLISHED`: el Publicador, `approve`, `POST /articles/{id}/publish`
y la siembra de demostración. `publish` publicaba cualquier borrador sin mirar nada y a quien fuera
admin o redactor, incluido el autor sobre su propio texto: la compuerta se podía saltar con una llamada.

### Qué se hizo y por qué

- `publication_gate/decision.py` (nuevo):
  - `can_publish(review, gate, approval, enforce)` — publica solo con **revisión que aprueba**
    (≥ 80, `coherent`, sin `not_verified`/`not_run`), **compuerta vigente y sin bloqueantes** y
    **aprobación humana del texto actual**. Con `PUBLICATION_GATE_ENFORCE=false` las dos primeras
    pasan a avisos; la aprobación humana sigue siendo obligatoria.
  - `assign_published(article, decisión)` — **el único sitio que asigna `ArticleStatus.PUBLISHED`**; sin una
    decisión que lo permita lanza `PermissionError`.
- **La revisión viaja con el informe:** el Publicador guarda la revisión de esa ejecución
  (`review_status`, nota, `coherent`) en `criteria["review"]`; sin Revisor en el flujo queda `not_run`,
  que no aprueba. Fuera del pipeline ya no queda otro rastro de ella, y `can_publish` la lee de aquí.
- `routers/articles.py`: `approve` y `publish` pasan por `_publish_through_the_gate` — mismas reglas
  (revisor asignado o admin, nunca el propietario, autor responsable, compuerta) y la misma
  `can_publish`. `publish` **evalúa la compuerta si no hay informe vigente** y conserva el informe aunque
  después se rechace; ya no publica borradores sin comprobar.
- Publicador de un proyecto sin `gate:` → `assign_published(legacy_decision())`. La siembra de
  desarrollo → `assign_published(dev_seed_decision())`, que exige `ENABLE_DEV_SEED`; el artículo de
  ejemplo nace `draft` y pasa por la puerta.
- **Verificable, no una intención:** `test_nada_asigna_published_salvo_can_publish` recorre `app/` y
  falla si aparece otra asignación fuera de `decision.py`. El dominio hexagonal sin usar
  `modules/articles` (tiene su propio enum y un `publish()` sin compuerta) se excluye explícitamente, y un
  segundo test falla si alguien lo conecta.
- `review.py`: `review_status = "not_run"` → `review_missing`.

### Definition of Done

- [x] **AC10** — una sola función decide; tabla de verdad completa (84 combinaciones); un 80 con un
  bloqueante abierto no publica; único punto de asignación por inspección estática.
- [x] **AC13** — los tres caminos (agente, `approve`, `publish`) consultan `can_publish`; `publish`
  evalúa el texto actual si no hay informe vigente y aplica las reglas de `approve`.
- [x] Tests: `backend/tests/test_can_publish.py` (103). Suite: 1337 pasados; los mismos 4 fallos que `develop`.
  Gate EDD sin regresión.
- [ ] Frontend: aún no entiende los códigos 409 ni el estado nuevo (T20.14).

### Verificación

SQLite y referencias resueltas con un simulado; no se ejecutó un pipeline con un LLM real.

### Fuera de alcance / notas

- **Cambios visibles al desplegar:**
  - `publish` ya no lo puede usar el autor ni un redactor sin ser revisor asignado: solo un admin o el
    revisor asignado que no sea propietario.
  - Un artículo escrito a mano **sin ejecutar el pipeline** no tiene revisión, así que no puede
    publicarse (`review_missing`) salvo con `PUBLICATION_GATE_ENFORCE=false`. Para publicar texto propio
    hay que pasarlo por el pipeline con el Revisor (`revisor → formateador → publicador`, que las reglas
    de flujo ya permiten sobre un artículo con cuerpo).
- `test_audit_log::test_publishing_an_article_is_audited` publicaba un borrador como su propia autora, que
  es justo el atajo que esta tarea cierra: ahora lo publica un admin no propietario con un informe vigente.
- La reevaluación por `publish` conserva la revisión del informe anterior; si el texto lo editó una
  persona después, esa revisión es de la versión anterior (lo cubre la aprobación humana de la huella).
