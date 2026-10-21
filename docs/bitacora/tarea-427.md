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

## 2026-10-21 — Fase 1: spec, ADR y regla de bitácora (documentación)

- **Ramas / PRs:** `docs/gobernanza-bitacora-obligatoria` → #426 · `docs/spec-032-compuerta-publicacion` → #429 · `docs/spec-032-ready` → #430 (todas mergeadas en `develop`)
- **Spec/ADR:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md), [ADR-0011](../adr/0011-publication-gate-fail-closed.md)
- **Dependencias:** Fase 0 (matriz de implementación, #428)

### Dónde estaba el problema

- **Gobernanza** (`docs/governance/GOVERNANCE.md` §3.1.2 y §6): pedía bitácora solo por tarea
  resuelta por un agente. No cubría fixes o parches hechos a mano, no exigía el *porqué* ni que
  viajara en la misma PR. Resultado visible: las bitácoras de #415–#419 se empujaron tras el
  merge y hubo que añadirlas aparte en #420.
- **Publicación** (`publicador.py`, `routers/articles.py`, `revisor.py`, `routing.py`): no existe
  compuerta; hay **tres** caminos a `PUBLISHED` (el agente, `approve` y `POST /articles/{id}/publish`)
  y ninguno valida; el Revisor falla abierto; tras 3 vueltas el flujo avanza.

### Qué se hizo y por qué

- **#426:** amplía GOVERNANCE §3.1.2 a todo fix/implementación/parche, con qué, por qué, cuándo
  y dónde, en la misma PR; añade la bitácora al DoD (§6), a la plantilla de `docs/bitacora/README.md`
  y a `CLAUDE.md`.
- **#429:** crea SPEC-032 (Draft) con la decisión de V09 (opción «a»: resolver contra
  Crossref/OpenAlex, falla cerrada, sin excepción para documentos internos), 16 criterios de
  aceptación y 15 tareas (T20.1–T20.15); ADR-0011; y el checklist de requisitos
  (`docs/specs/checklists/SPEC-032-publication-gate.md`).
- **Clarificación (5 preguntas):** `not_implemented` no bloquea; umbrales de coincidencia de V09;
  quién aprueba; V03 como IMRaD por defecto; estado `requires_human_review`.
- **Análisis (`/speckit-analyze`):** halló un tercer camino a `published` (`/publish`), la falta de
  ADR y de plan de evaluación EDD; se corrigió en la misma spec (AC13–AC16, ADR-0011, §6).
- **#430:** pasa SPEC-032 a Ready para que `/sdd-sync` pueda sembrar la épica E20.

### Definition of Done

- [x] Spec validada con `scripts/validate_specs.py` (SPEC-032 y checklist).
- [x] ADR-0011 creado e indexado.
- [x] Tests de gobernanza (`test_sdd_governance.py`) en verde; el único fallo del conjunto,
  `test_la_spec_de_finetune_sigue_en_draft` (SPEC-031), ya fallaba en `develop`.
- [ ] **Checklist de requisitos:** 33/43 puntos cumplidos; 10 abiertos (fuentes que Crossref/OpenAlex
  no indexan, quién declara al autor responsable, «et al.» y alias de revista, aprobaciones
  concurrentes, recuperación ante fallos, referencias duplicadas, manuscritos sin referencias,
  nombres de métricas, cobertura real del corpus).

### Verificación

- Solo documentación: ni se tocó código de producto ni se ejecutó el pipeline.
- Falta de evidencia honesta: la regla de bitácora de #426 **no tuvo bitácora propia**, y #429/#430
  tampoco, hasta esta entrada. #426 y #429 no tenían issue porque `/sdd-sync` aún no había
  sembrado la épica E20.

### Fuera de alcance / notas

- Siguiente paso: `/sdd-sync` en dry-run y, con visto bueno, `--apply` para crear la épica E20 y
  T20.1–T20.15; después implementación por las tareas sin dependencias.
- **Hecho el 2026-10-21:** `/sdd-sync --apply` (contra `onpremialabs/swarm-platform-builder`) creó la
  épica E20 = #432 y T20.1–T20.15 = #433–#447, como sub-issues de #432 y dentro del Project 8, sin
  ningún UPDATE (T8.3/#209 y T11.5/#251 difieren solo en tildes y no se tocaron). El campo `Epic`
  del Project 8 no tiene la opción `E20`: queda vacío hasta que una persona la añada.
- La implementación empezará con el gate EDD y la regresión explicada en la misma PR (T20.15).
