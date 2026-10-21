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

## 2026-10-21 — Actualización: criterios V01–V16 con el Framework v0.1

- **Rama:** `docs/fw-fase0-matriz-implementacion` (misma PR #428)

### Qué se hizo y por qué

Se recibió el *Framework de redacción y validación de papers* v0.1 (PDF, 29/09/2026), que
define los criterios que faltaban. Se reescribió la tabla por criterio de
[`docs/reports/matriz-implementacion.md`](../reports/matriz-implementacion.md) con las
definiciones reales de §9 (tipo, verificación y responsable), y se añadió un contraste con
las reglas de §3, §10 y §20.

- Resultado: **11 criterios ausentes** (V01, V02, V04–V08, V10, V11, V14, V15), **5 parciales**
  (V03, V09, V12, V13, V16) y **ninguno implementado**.
- Reglas del framework que el código incumple: el Formateador reescribe el cuerpo con un LLM
  (el framework dice que no cambia); el Redactor añade fuentes por su cuenta; el Investigador
  genera texto; falla abierto el Revisor; tras 3 vueltas se publica.
- **Implicación de diseño no recogida en el plan:** V09 nivel 1 exige que toda referencia
  venga de una base bibliográfica con DOI/PMID; las fuentes actuales son documentos subidos
  al RAG sin identificador, así que casi ninguna pasaría. Hay que decidir cómo resolverlas
  (Crossref por título, excepción documentada o solo búsqueda externa) antes de 1.2/1.3 y D2.
- Diferencias plan ↔ framework: V07/V08 solo bloquean en revisiones; «otra familia» de modelo
  para el Revisor es propuesta (FW-4), no requisito.

### Definition of Done

- [x] **AC3** — V01–V16 completados con el framework.
- [ ] **AC2 (0.1)** — sigue pendiente. Se buscó en todo el repo, el historial de git,
  `backend/evals/results` y `backend/data/dev.db`: PR-FW-001 no está. Hace falta el `article_id`
  de esa ejecución, el texto publicado (`articles.body`) y lo que la traza no guarda
  (`output_text` se recorta a 4000 caracteres y el feedback del Revisor no se persiste).

### Fuera de alcance / notas

- El framework solo existe como PDF fuera del repo; conviene versionarlo.
