# Tarea #447 — T20.15 Evaluación EDD: datasets y umbrales actualizados y regresión sin fallos nuevos

## 2026-10-21 — Éxito ✅ (con el límite de siempre: `replay` y `handwritten`)

- **Rama:** `feat/t20-15-evaluacion-edd`
- **PR:** la de esta rama → `develop` (`Closes #447`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC12 y §6 (Evaluación) · épica E20 (#432)
- **Dependencias:** T20.7 (#439) y T20.11 (#443), ya en `develop`

### Dónde estaba el problema

SPEC-032 cambia cuatro agentes (Revisor, Redactor, Formateador, Investigador) y GOVERNANCE §5/§6 exige actualizar
sus datasets de EDD en la misma PR que el cambio. Las PRs de E20 ya lo habían hecho para el Redactor (#437) y el
Revisor (#439), pero quedaban sin cubrir los cambios del Formateador y del Investigador (T20.2): que una referencia
con campos vacíos **dejara de omitirse en silencio**. El gate pasaba, pero en `replay`, que reproduce salidas grabadas:
no ejecutaba el código nuevo, así que no habría detectado la regresión que justo se quería evitar.

### Qué se hizo y por qué

- **Métrica nueva `reference_completeness`** (`evals/agent_behavior/metrics/reference_completeness.py`, registrada y
  documentada en el README del harness): determinista, sobre el texto; lee la sección de referencias y exige a cada
  entrada **año e identificador resoluble** (DOI o enlace). Solo aplica a los casos que declaran
  `complete_references`. Un texto sin sección de referencias no se da por bueno.
- **`formateador-golden`:** el caso IEEE declara `complete_references` y sus tres referencias llevan año e
  identificador. Los identificadores `10.0000/fixture-*` son **marcadores de un fixture escrito a mano**, no DOI reales.
- **`formateador-regressions`:** caso nuevo `referencia-incompleta-impresa` (un nombre de archivo, una referencia sin
  año y una sin identificador). Falla a propósito, y solo lo detecta la métrica nueva, no la de formato.
- **`thresholds.yaml`:** `reference_completeness: {min: 100, baseline: 100.0}` para el Formateador. `enforce`
  sigue en `false`.
- `docs/specs`: SPEC-032 pasa de `Ready` a **`In progress`**.
- Se verifica además que siguen en pie los cambios de datasets de T20.5 (Redactor: Resultados y Discusión) y T20.7
  (Revisor: `revisor-sin-veredicto`).

### Definition of Done

- [x] **AC12 — sin fallos nuevos:** suite completa 1371 pasados, 4 fallos, **los mismos que `develop`**
  (`test_frontend_layers` ×2 por rutas con `\` en Windows, `test_no_tracked_databases` por un bloqueo de archivo de
  Windows, `test_la_spec_de_finetune_sigue_en_draft` de SPEC-031).
- [x] **AC12 — gate EDD sin regresión:** `python -m evals.agent_behavior.gate` → «Ninguna métrica por debajo de su
  umbral», con la métrica nueva incluida.
- [x] Tests: `backend/tests/test_edd_spec032.py` (10), incluida la comprobación de que cada regresión de E20 la
  detecta la métrica que debe.
- [ ] **Medir el comportamiento real:** el gate corre en `replay` sobre salidas `handwritten`. Un verde dice que
  **las métricas funcionan**, no que el Formateador, el Revisor o el Redactor se comporten así con un modelo real.
  Para eso hay que regrabar los golden en `--mode live`, pasar su `provenance` a `recorded` y poner `enforce: true`.

### Verificación

Replay. No se ejecutó ningún agente contra un LLM.

### Fuera de alcance / notas

- El Investigador no necesitó caso nuevo: conserva `journal`, `year` y `doi` del documento (T20.2) y su golden no
  declara esos campos como exigidos.
- `reference_completeness` es la parte observable **desde el texto** de la regla de la compuerta (que opera sobre
  fuentes estructuradas); no la sustituye.

## Estado de la épica E20 tras esta PR

Las 15 tareas (#433–#447) están implementadas y con bitácora. **SPEC-032 no pasa a `Done`**, porque quedan criterios
sin verificar de verdad (ver cada bitácora):

- **AC3 (≥ 90 % de resolución):** medido solo con registros simulados; falta contra Crossref/OpenAlex reales.
- **Migración `0006` en Postgres** (`ALTER TYPE … ADD VALUE`): probada solo en SQLite.
- **Interfaz (T20.14):** compilada y comprobada de forma estructural, no en un navegador.
- **Comportamiento con un LLM real** (Revisor falla cerrado, Redactor separa secciones, Formateador no omite).
- **Condiciones de uso de Crossref/OpenAlex** para títulos de trabajos inéditos (FW §20.7).
- **Checklist de la spec:** 33/43; los 10 puntos abiertos siguen sin resolver.
- **Decisiones D1–D5** del plan y artefactos de PR-FW-001 (Fase 0, tarea 0.1).
