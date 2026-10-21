# Tarea #427 — FW-F0 Línea base y diagnóstico de código (plan de mejoras del pipeline)

## 2026-10-21 — Parcial 🟡 (diagnóstico de código hecho; faltan insumos externos)

- **Rama:** `docs/fw-fase0-matriz-implementacion`
- **PR:** la de esta rama → `develop` (`Refs #427`, no la cierra: faltan AC2 y AC3)
- **Origen:** plan `plan-implementacion-mejoras-swarm-framework.md`, Fase 0
- **Dependencias:** ninguna. Habilita las fases 1 a 5.

### Dónde estaba el problema

No había un mapa fiable de qué cumple ya el pipeline. El informe «Framework vs. plataforma
actual» marcaba varios puntos como «no evidenciado» sin inspección de código.

### Qué se hizo y por qué

Lectura sin cambios de código de `revisor.py`, `formateador.py`, `publicador.py`,
`investigador.py`, `redactor.py`, `platform/engine/routing.py`, `platform/capabilities/rag.py`,
`application/use_cases.py` y `routers/articles.py`. Resultado en
[`docs/reports/matriz-implementacion.md`](../reports/matriz-implementacion.md). Lo más
relevante:

- El Publicador **no usa LLM ni valida nada**; el «parámetro de modelo» es un artefacto de la
  traza (`use_cases.py` resuelve un modelo para todos los agentes).
- El Revisor **falla abierto**: sin JSON válido aprueba con 85; con error inventa una revisión.
- Tras 3 vueltas el flujo **avanza igualmente** a publicar.
- El Investigador solo usa RAG local, sin búsqueda externa, y las fuentes salen con
  `year`, `journal` y `doi` vacíos; `RAG_SCORE_THRESHOLD` es configuración sin uso.
- La aprobación humana ya existe (`/articles/{id}/approve`) pero el agente la salta.

### Definition of Done

- [x] **AC1** — todos los puntos «no evidenciado» de 0.2–0.6 resueltos con referencia a código.
- [ ] **AC2 (0.1)** — archivar artefactos de PR-FW-001: **no hecho**, no están en el repo.
- [ ] **AC3** — completar V02, V03, V04, V06, V08, V11 y V15: **no hecho**, el repo no contiene
  el Framework v0.1 y no se quiso adivinar su definición.

### Verificación

- Solo lectura; no se ejecutó el pipeline. Las afirmaciones son sobre lo que dice el código,
  no sobre lo ocurrido en PR-FW-001.

### Fuera de alcance / notas

- Sin código de producto modificado. Las fases 1 y siguientes quedan sin empezar: dependen de
  esta matriz y, la 3, 4 y 5, de las decisiones D1–D5 del plan.
