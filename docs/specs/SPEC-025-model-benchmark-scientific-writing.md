# SPEC-025: Benchmark comparativo de modelos LLM open-source para redacción científica

- **Estado:** Draft
- **Autor:** Comisión de evaluación de modelos (plataforma AlejandrIA Magazine)
- **Fecha:** 2026-08-09
- **Épica:** E13 (Benchmark y selección de modelos base para redacción científica)
- **ADR relacionado:** ADR-0006 (complementa; ver nota de alcance en §1); ver
  también nota sobre ADR-0009 más abajo.
- **Severidad:** N/A — mejora de capacidad, no remediación de seguridad.

> **Draft**: pendiente `/speckit-clarify` / `/speckit-checklist` antes de pasar a
> `Ready`. Mientras esté en Draft, `/sdd-sync` no siembra su épica/tareas en el
> GitHub Project (§ [docs/specs/README.md](README.md)).
>
> **Renumerada de SPEC-023 a SPEC-025 (2026-08-10):** esta spec se creó
> originalmente como "SPEC-023" en una sesión de trabajo local, desconectada de
> GitHub. En paralelo, en el repositorio real se mergeó
> [SPEC-023](SPEC-023-claude-default-engine.md) (Claude como motor agéntico por
> defecto, [ADR-0009](../adr/0009-claude-default-agentic-engine.md)), que
> reclamó ese número y la épica E12. Esta spec se renumeró a SPEC-025/E13
> (tareas T13.1–T13.4) para no colisionar; su contenido no cambió en sustancia.

## 1. Problema

Los modelos usados por cada agente del pipeline editorial están fijados hoy sin
comparación documentada: `mistral:7b`/`llama3.2:1b` (Investigador),
`llama3.2:3b` (Redactor y Revisor), `llama3.2:1b` (Formateador) — ver
[`backend/app/shared/agents_seed.py`](../../backend/app/shared/agents_seed.py)
y los perfiles `backend/app/agents/*.agent.md`. No hay evidencia versionada de
por qué esos modelos y no otros equivalentes open-source, ni de su relación
razonamiento/coste-de-cómputo para las tareas concretas del pipeline (síntesis
de fuentes, redacción académica estructurada, revisión con score 0-100,
normalización de citas).

**Nota de alcance frente a [ADR-0009](../adr/0009-claude-default-agentic-engine.md)
(Claude por defecto, mergeado en paralelo a este trabajo):** el proveedor por
defecto de la plataforma ya no es Ollama, sino Claude/Anthropic, con
`.agent.md` `models: {anthropic: ..., ollama: ...}` por proveedor. Este
benchmark evalúa específicamente la **ruta on-prem/Ollama** (`models.ollama`
por agente) — la opción de despliegue sin dependencia de un proveedor cloud,
no "el motor por defecto" de la plataforma. Sigue siendo la comparación
relevante para quien despliegue con `LLM_PROVIDER=ollama`.

**Nota de alcance frente a [ADR-0006](../adr/0006-adopt-evaluation-driven-development.md):**
EDD gobierna deliberadamente el *comportamiento* de los agentes ya configurados
sobre un modelo dado (fidelidad de citas, calibración, regresión de prompt) y
excluye explícitamente el *benchmarking de proveedores/modelos foundation*.
Esta spec cubre precisamente esa capa **anterior y complementaria**: elegir con
criterio el modelo base de cada agente, con razonamiento y capacidad de
cómputo como criterios explícitos, antes de que EDD vigile su comportamiento en
producción. No reabre ni contradice ADR-0006.

## 2. Objetivos / No-objetivos

- **Objetivos:**
  - Comparar un conjunto acotado de modelos open-source ejecutables vía Ollama
    sobre las cuatro tareas reales del pipeline (síntesis de investigación,
    redacción de borrador, revisión con score, formateo de citas).
  - Medir **razonamiento/calidad** (coherencia, fidelidad a las fuentes,
    seguimiento de instrucciones estructuradas, calidad del score del Revisor)
    y **capacidad de cómputo** (latencia, tokens/s, RAM/VRAM pico) en hardware
    representativo del despliegue objetivo.
  - Producir un **informe comparativo versionado** en el repo con una
    recomendación priorizada de modelo por agente.
  - Dejar un **harness re-ejecutable** para repetir la comparación cuando
    aparezcan nuevos modelos candidatos.
- **No-objetivos:**
  - Fine-tuning o entrenamiento de modelos.
  - Evaluar proveedores cloud de pago (OpenAI/Azure/Groq) más allá de una
    mención comparativa de referencia — el foco es *open-source* ejecutable
    on-prem, coherente con el stack Ollama de la plataforma.
  - Sustituir o solapar con el harness EDD de `backend/evals/` (ADR-0006):
    ese harness evalúa el comportamiento de los agentes *ya configurados*;
    este benchmark evalúa modelos *foundation* candidatos antes de configurar
    nada.
  - Cubrir el catálogo completo de Ollama: el set de candidatos es acotado y
    explícito (ver §8).

## 3. Criterios de aceptación (Given/When/Then)

- [x] **AC1** — *Given* un conjunto de modelos candidatos ejecutables
  localmente (mínimo 3, ver épica E13/T13.1), *When* se ejecuta el harness de
  benchmark sobre un dataset fijo de prompts representativos de las cuatro
  tareas del pipeline, *Then* se genera un **informe comparativo versionado**
  en el repo con métricas de razonamiento/calidad y de cómputo (latencia,
  tokens/s, RAM pico) por modelo y por rol de agente. — Cumplido:
  [docs/reports/model-benchmark-scientific-writing.md](../reports/model-benchmark-scientific-writing.md)
  (8 modelos candidatos, incluida referencia documentada de no-viabilidad de
  `llama3-chatqa:70b` en este hardware).
- [x] **AC2** — *Given* el informe generado (AC1), *When* el equipo/comisión lo
  revisa, *Then* el propio documento registra la **selección final de
  modelo(s) por agente** con su justificación explícita en términos de
  razonamiento vs. capacidad de cómputo disponible. — Borrador de selección
  registrado en el informe (§"Selección"), **pendiente de ratificación
  explícita de la comisión** antes de considerarse definitivo.
- [x] **AC3** — *Given* los modelos seleccionados (AC2), *When* se actualiza la
  configuración de agentes vía el frontmatter `models.ollama` de
  `backend/app/agents/*.agent.md` (namespace on-prem — ver nota de alcance
  ADR-0009 arriba; `resolve_agent_model()` en
  [`platform/llm.py`](../../backend/app/platform/llm.py) prioriza
  `models[<proveedor activo>]` sobre el campo `model` legado), *Then* los
  agentes del pipeline usan efectivamente esos modelos cuando
  `LLM_PROVIDER=ollama`, verificable vía `GET /api/v1/agents/claude-defs?project_id=`
  y una ejecución completa del pipeline con ese proveedor activo. — Cumplido:
  `backend/app/agents/{investigador,revisor,formateador}.agent.md` actualizados
  en **ambos** campos (`model` legado y `models.ollama`, mantenidos en sync
  como hace el resto de agentes desde ADR-0009): investigador→`gemma2:2b`,
  revisor→`llama3.2:1b`, formateador→`llama3.2:3b` (redactor sin cambio);
  perfiles ya sembrados sincronizados vía `PUT /claude-defs/{id}`, y corrida
  real de punta a punta (`investigador → redactor → revisor → formateador →
  publicador`) verificada con estado final `published` bajo
  `LLM_PROVIDER=ollama`.
- [x] **AC4** — *Given* el harness de benchmark, *Then* es **re-ejecutable**
  (script versionado, sin dependencias de pago ni servicios externos) para
  repetir la comparación cuando se quieran evaluar nuevos modelos candidatos.
  — Cumplido: `evals/model_benchmark/run_benchmark.py` (CLI con `--models`),
  smoke tests en `backend/tests/test_model_benchmark_smoke.py`.

Cada AC es verificable: AC1/AC4 por ejecución del script y presencia del
informe; AC2 por revisión del documento; AC3 por inspección de configuración +
una corrida real del pipeline.

## 4. Diseño propuesto

- **Harness**: `backend/evals/model_benchmark/` (carpeta hermana, no dentro
  del harness EDD de `backend/evals/` que evalúa comportamiento de agentes ya
  configurados — ver nota de alcance §1). Contiene:
  - `dataset.py` — prompts fijos por rol (síntesis con fuentes, redacción de
    borrador con esquema dado, revisión de un borrador de referencia con score
    esperado aproximado, formateo de citas a un estilo dado).
  - `run_benchmark.py` — itera modelo × prompt vía el dispatcher
    `backend/app/shared/llm.py` (reutiliza el cliente Ollama existente, no uno
    nuevo), mide latencia y tokens/s, captura RAM/VRAM del proceso Ollama.
  - Rúbrica de calidad: métricas deterministas donde sea posible (longitud,
    presencia de secciones esperadas, formato de citas válido) + *LLM-as-judge*
    opcional con `temperature=0` para coherencia (coherente con el enfoque de
    ADR-0006, aplicado aquí a modelos candidatos en vez de a agentes).
- **Informe**: `docs/reports/model-benchmark-scientific-writing.md` (tablas por
  modelo/rol + recomendación final, sección "Selección" para AC2).
- **Aplicación de la selección (T13.4)**: cambios acotados en
  `agents_seed.py` / `.agent.md` / `config.yaml` — sin tocar el orquestador.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Hardware de desarrollo limitado (sin GPU dedicada) sesga los resultados de latencia frente a un despliegue con GPU | Medio | El informe reporta el hardware usado explícitamente; se prioriza el ranking de razonamiento/calidad como criterio principal y el de cómputo como filtro de viabilidad, no al revés |
| *LLM-as-judge* introduce sesgo o varianza | Medio | `temperature=0`, rúbrica fija y determinista donde sea posible; el juez es explícito en el informe |
| Dataset de prompts no representativo de casos reales | Alto | Prompts derivados de los `.agent.md` reales y de artículos de ejemplo ya sembrados (`_seed_default_project_content`) |
| Selección de modelo queda "a ojo" sin trazabilidad | Medio | AC2 obliga a documentar la justificación en el propio informe versionado |

## 6. Plan de pruebas

- Test de humo del harness: ejecuta con un modelo pequeño (`llama3.2:1b`) y
  valida que produce el informe con las secciones esperadas, sin requerir red
  (mock del cliente LLM para CI; ejecución real solo local/manual).
- Validación manual: revisión de la comisión sobre el informe generado (AC2).
- Tras aplicar la selección (T13.4): correr el pipeline completo
  (`investigador → redactor → revisor → formateador → publicador`) en local y
  confirmar que usa los modelos configurados (AC3).

## 7. Impacto operativo / observabilidad

- Sin cambios de esquema de BD ni de API pública.
- `config.yaml` / `agents_seed.py` pueden cambiar los modelos por defecto por
  agente tras T13.4 — afecta tiempos de respuesta y uso de RAM del pipeline en
  producción; documentar el cambio en el changelog.
- El informe (`docs/reports/`) queda versionado para auditoría futura y como
  base para repetir el benchmark (AC4) cuando cambien los candidatos.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E13
  title: "Benchmark y selección de modelos base para redacción científica"
  area: area/evaluation
tasks:
  - id: T13.1
    title: Dataset y harness de benchmark de modelos base (prompts fijos por rol + métricas de cómputo)
    sev: high
    depends_on: []
    acceptance: [AC1, AC4]
  - id: T13.2
    title: Ejecutar el benchmark sobre el set de modelos candidatos y producir el informe comparativo versionado
    sev: high
    depends_on: [T13.1]
    acceptance: [AC1]
  - id: T13.3
    title: Selección de modelo(s) por agente documentada y aprobada por la comisión
    sev: medium
    depends_on: [T13.2]
    acceptance: [AC2]
  - id: T13.4
    title: Aplicar la selección a la configuración de agentes (agents_seed.py / .agent.md / config.yaml)
    sev: medium
    depends_on: [T13.3]
    acceptance: [AC3]
```
