# Épica #432 — E20 Compuerta de publicación: medición real, verificación en Postgres y pendientes

## 2026-10-21 — Cierre de lo preparable de E20

- **Rama:** `feat/e20-medicion-ac3-y-pendientes`
- **PR:** la de esta rama → `develop` (`Refs #432`, no cierra la épica: quedan criterios por verificar)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md)
- **Contexto:** las 15 tareas de E20 (#433–#447) están mergeadas. Esta PR reúne lo que se podía **preparar o medir** sin una
  decisión humana, y deja lo demás documentado.

### Dónde estaba el problema

Los tests de E20 prueban la lógica con simulados, así que quedaban sin verificar de verdad: la tasa de resolución de AC3
contra Crossref/OpenAlex, la migración en Postgres y la interfaz; y el framework (fuente de verdad del plan) solo existía como PDF fuera
del repositorio.

### Qué se hizo y por qué

- **Medición real de AC3** — `scripts/measure_reference_resolution.py` y `backend/evals/reference_resolution/references.jsonl`
  (38 referencias: 20 válidas con DOI, 12 de ellas sin DOI, 6 controles negativos). Con red real, la primera pasada dio **17/20
  (85 %)**: **no cumplía**. Informe y análisis en [`docs/reports/medicion-ac3-spec-032.md`](../reports/medicion-ac3-spec-032.md).
- **Dos correcciones del resolutor, medidas y probadas** (`reference_resolver.py`):
  1. La **revista** se comparaba demasiado literal («Proc. IEEE Conf. …» frente a «2016 IEEE Conference …» fallaba). Ahora ignora palabras
     genéricas y números, tolera orden y abreviaturas y exige ≥ 60 % de coincidencia; sigue distinguiendo «Nature» de «Science».
  2. Si varios registros encajan por título y autores, **el año y la revista de la cita desempatan** (antes se rendía); si siguen varios o
     ninguno, `not_verified`.
  Resultado: **18/20 (90 %) con DOI, 10/12 sin DOI, 6/6 controles negativos bloqueados, 0 falsas aceptaciones.**
- **Job de CI `migrations-postgres`** (`.github/workflows/ci.yml`) y `scripts/verify_postgres_schema.py`: aplica toda la cadena de Alembic
  en Postgres 16, comprueba `alembic check`, que el enum nativo `articlestatus` ganó `REQUIRES_HUMAN_REVIEW`, las columnas y claves ajenas
  de SPEC-032, y que bajar y subir la última revisión funciona. Es la comprobación que la CI con SQLite no puede hacer.
- **Framework versionado:** `docs/framework/framework-redaccion-validacion-papers-v0.1.pdf` con su README (hasta ahora solo existía
  fuera del repositorio). El repo es privado.
- **Documentación de lo pendiente:** [`spec-032-decisiones-pendientes.md`](../reports/spec-032-decisiones-pendientes.md) (8 hallazgos con
  recomendación, los 10 puntos abiertos del checklist, D1–D5) y [`spec-032-verificacion-manual.md`](../qa/spec-032-verificacion-manual.md)
  (QA de la interfaz, del LLM real y de lo operativo, incluidas las verificaciones aún sin hacer de BUG-003/BUG-005/UX-002).
- **SPEC-032:** sección *Clarifications* con los hechos de la implementación y la medición; checklist: CHK034 y CHK037 marcadas (35/43).
- **Arreglo de un test que fallaba solo en Windows:** `test_frontend_layers.py` comparaba rutas con `/` y salían con `\`.

### Definition of Done

- [x] Medición con la red hecha y registrada, con sus límites dichos.
- [x] Correcciones del resolutor con tests offline (`backend/tests/test_reference_measurement.py`, 16).
- [x] Suite: 1389 pasados, **2 fallos preexistentes** (antes 4): `test_no_tracked_databases` (bloqueo de archivo de Windows) y
  `test_la_spec_de_finetune_sigue_en_draft` (SPEC-031 ya no está en `Draft`; no es de E20).
- [ ] **El job `migrations-postgres` es nuevo y no se ha ejecutado aún**: su primer resultado es el de esta PR. No hay Docker ni Postgres
  en la máquina donde se preparó.
- [ ] AC3 **no se da por verificado**: el 90 % es exactamente 18/20 sobre una muestra pequeña escrita de memoria. Falta repetirlo con un
  conjunto revisado y de la revista real.

### Verificación

La medición usó Crossref y OpenAlex reales (38 referencias, secuenciales). Los controles negativos nunca pasaron.

### Fuera de alcance / notas

- **No se ha implementado DataCite** (los DOI de arXiv, `10.48550/*`, los emite DataCite y Crossref responde 404): los dos únicos fallos con
  DOI son de arXiv. Es la decisión DEC-1, que enmienda ADR-0011 (un host más en el camino crítico de publicar).
- No se tocó SPEC-031 ni `modules/articles` (código muerto): quedan como DEC-8 y DEC-5.
- El PDF del framework se copió tal cual desde `Descargas` (había dos ficheros idénticos, mismo tamaño). Si no debe vivir en el repo, se quita en
  la revisión de esta PR.
