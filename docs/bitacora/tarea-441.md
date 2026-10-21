# Tarea #441 — T20.9 Compuerta con bloqueantes devuelve el artículo a draft con informe y agente responsable

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-9-compuerta-en-publicador`
- **PR:** la de esta rama → `develop` (`Closes #441`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC14, y de AC5/AC8 la parte del Publicador · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.4 (#436) y T20.6 (#438), ya en `develop`

### Dónde estaba el problema

`adapters/publicador.py` escribía el texto y marcaba el artículo `PUBLISHED` sin comprobar nada. La
compuerta existía (T20.4) y se guardaba (T20.6), pero ningún agente la ejecutaba: el pipeline seguía
publicando por su cuenta.

### Qué se hizo y por qué

- **Publicador** (`_apply_gate`): tras persistir el texto final y la maquetación, evalúa la compuerta
  sobre ese texto (`formatted_text`), guarda el informe ligado a la ejecución y fija el estado:
  - sin bloqueantes → **`in_review`**, a la espera de `approve` (T20.10);
  - con bloqueantes → **`draft`**, con el informe y, por cada bloqueante, criterio, evidencia y
    `responsible_agent`;
  - con `PUBLICATION_GATE_ENFORCE=false` los bloqueantes se registran y avisan, pero pasa a `in_review`.
  El agente **ya no asigna `published`** (AC8). Sigue sin llamar al LLM.
- **Evento SSE `gate_failed`** (`use_cases.py`) con los bloqueantes, tras `agent_end`; el orquestador
  pasa `_run_id` al agente para ligar el informe a la ejecución. `gate_failed` y `gate_blockers`
  entran en `AgentState`.
- **`gate.responsible` en `template.yaml`** (criterio → agente: referencias → `investigador`,
  marcadores y estructura → `redactor`), validado al cargar: un agente no declarado es `TemplateError`.
  La devolución automática es de la Fase 2; hoy se informa y una persona reejecuta o reevalúa.
- **Reejecutar invalida la aprobación:** el texto cambia, así que `approved_*` y `published_at` se
  limpian y un artículo que estaba `published` vuelve a `in_review`/`draft`. Es el comportamiento que
  ADR-0011 pide (la aprobación está ligada a la huella del texto) pero **es un cambio visible**.
- **Proyecto sin `gate:`** conserva el comportamiento anterior (publica): la compuerta es opcional por
  proyecto.

### Definition of Done

- [x] **AC14** — compuerta con bloqueantes → `draft`, informe con criterio, evidencia y agente
  responsable, evento `gate_failed`; no se publica ni se envía a revisión.
- [x] **AC8 (Publicador)** — termina en `in_review`, nunca `published`.
- [x] **AC5** — se evalúa sobre `formatted_text`; los criterios pendientes constan en el informe.
- [x] Tests: `backend/tests/test_publicador_compuerta.py` (11). Suite: 1218 pasados, los mismos 4
  fallos que `develop`. Gate EDD sin regresión (no hay dataset del Publicador).
- [ ] `publish` directo y `can_publish` como única puerta: T20.11 (#443).
- [ ] Frontend: el evento `gate_failed` y el estado nuevo aún no se muestran (T20.14).

### Verificación

Con SQLite y las referencias resueltas por un simulado; no se ejecutó el pipeline completo con un LLM
real ni contra Crossref/OpenAlex.

### Fuera de alcance / notas

- **Consecuencia práctica que conviene saber:** hoy casi ningún artículo pasará la compuerta, porque
  las fuentes salen del RAG sin DOI y los documentos subidos a mano quedan `not_verified` (ADR-0011).
  El autor puede aportar el DOI (campo `doi` del documento); el flujo de aportarlo a mano desde la
  interfaz no está construido. Para desplegar sobre un entorno vivo, empezar con
  `PUBLICATION_GATE_ENFORCE=false`.
- Sin fuentes estructuradas el criterio de referencias es `not_verified`: un manuscrito sin
  referencias comprobables no se aprueba por ausencia.
