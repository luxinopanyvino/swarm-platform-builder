# Tarea #440 — T20.8 Estado «requiere revisión humana» tras 3 vueltas con bloqueantes

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-8-revision-humana-tras-vueltas`
- **PR:** la de esta rama → `develop` (`Closes #440`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC7 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.6 (#438) y T20.7 (#439), ya en `develop`

### Dónde estaba el problema

`platform/engine/routing.py`: tras `max_loops` vueltas con la revisión sin aprobar, el enrutador
**avanzaba igualmente** al Formateador y al Publicador (`next_after`). El texto que el revisor había
rechazado tres veces se formateaba y se publicaba (matriz de la Fase 0).

### Qué se hizo y por qué

- **Motor** (`routing.py`): `ReviewLoop.on_exhausted` (`advance` por defecto, `stop`), `needs_rework` y
  `review_exhausted`. Con `stop`, al agotarse las vueltas el enrutador devuelve el fin: **no corren el
  Formateador ni el Publicador**. El motor sigue sin nombrar agentes ni estados.
- **`needs_rework` incluye `coherent = false`**, no solo la puntuación: era la definición de bloqueante
  de juicio (T20.7) pero el enrutador solo miraba la nota. El Revisor cuenta ahora la vuelta también por
  incoherencia (`loop_count`), o un revisor incoherente con nota alta habría girado sin tope.
- **Plantilla:** `on_exhausted: stop` en el bucle de AlejandrIA; el loader valida los valores.
- **Orquestador** (`use_cases._halt_for_human_review`): al terminar la ejecución detenida, el artículo
  pasa a **`requires_human_review`**, se guarda el último borrador en `body` y los comentarios del
  revisor (sin repetidos; el feedback se acumula entre vueltas) en `rejection_comment`, y se emite el
  evento SSE **`requires_human_review`** con puntuación, vueltas, `review_status` y comentarios, antes de `done`.
- **Salir del estado, solo una persona:** `reject` acepta ahora también `requires_human_review`
  (→ `rejected`); reejecutar (`/run`, no reanudación) lo devuelve a `draft` con los comentarios aún
  visibles y el contador a cero (el estado inicial lo reinicia). Una **reanudación** no cambia el estado
  y continúa del checkpoint, sin reiniciar el contador.
- Una decisión humana de «continuar» sigue mandando sobre el agotamiento.
- `test_project_template.py`: la forma esperada del grafo gana `on_exhausted="stop"`, único cambio
  deliberado respecto a la forma original.

### Definition of Done

- [x] **AC7** — 3 vueltas sin aprobar → `requires_human_review`, sin Formateador ni Publicador, evento SSE
  con puntuación y comentarios; solo reejecutar o `reject` salen; `resume` no reinicia el contador.
- [x] Tests: `backend/tests/test_review_exhausted.py` (16), incluido el pipeline completo con agentes
  simulados. Suite: 1234 pasados, los mismos 4 fallos que `develop`. Gate EDD sin regresión.
- [ ] Frontend: el estado y el evento aún no se muestran (T20.14).

### Verificación

Pipeline real de LangGraph con agentes simulados y base SQLite; no se ejecutó con un LLM real.

### Fuera de alcance / notas

- **Cambio visible:** con el revisor siempre rechazando (o el LLM caído, T20.7), la ejecución termina
  en `requires_human_review` en lugar de publicar. Otros proyectos conservan `advance` salvo que declaren `stop`.
- El `body` del artículo se sobrescribe con el último borrador al detenerse: es lo que la persona debe revisar.
- Un `resume` tras `requires_human_review` no cambia el estado; hay que reejecutar para salir.
