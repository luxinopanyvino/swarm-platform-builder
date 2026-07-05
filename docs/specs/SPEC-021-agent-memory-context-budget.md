# SPEC-021: Memoria a largo plazo y presupuesto de contexto de los agentes

- **Estado:** Draft
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E10 (Memoria y contexto de agentes)
- **ADR relacionado:** ADR-0008
- **Severidad:** 🟠

> **Draft deliberado** (pipeline ADR-0007): contiene marcadores
> `[NEEDS CLARIFICATION]` a resolver con `/speckit-clarify` y debe pasar
> `/speckit-checklist` antes de Ready. Mientras esté en Draft, `/sdd-sync`
> **no** siembra su épica/tareas.

## 1. Problema

Los prompts de los agentes se ensamblan **sin conteo de tokens** contra
ventanas fijas y pequeñas (`num_ctx=4096` en
[redactor.py:259](../../backend/app/modules/agents/adapters/redactor.py#L259),
[revisor.py:51](../../backend/app/modules/agents/adapters/revisor.py#L51),
[formateador.py:223](../../backend/app/modules/agents/adapters/formateador.py#L223);
`8192/2048` en [investigador.py:218](../../backend/app/modules/agents/adapters/investigador.py#L218)).
El estado crece con cada iteración del bucle Revisor→Redactor (borrador +
feedback + RAG) y, cuando la ocupación entra en el **último ~20% de la
ventana**, el modelo degrada (pérdida de instrucciones, "lost in the middle")
sin que nada lo detecte ni lo mitigue. Además **no existe memoria entre
ejecuciones**: cada run parte de cero (el único almacén es el RAG documental)
y la política de caché del LLM (`keep_alive=0` en cada llamada) es implícita
y no configurable por despliegue.

## 2. Objetivos / No-objetivos

- **Objetivos:** presupuesto de contexto por paso con recorte priorizado;
  compactación del historial bajo presión; memoria episódica por proyecto
  entre ejecuciones; política de caché explícita y uso de contexto observable.
- **No-objetivos:** aumentar `num_ctx`/cambiar de modelos como solución;
  memoria conversacional completa; fine-tuning; caché semántica de respuestas.

## Clarifications

### Session 2026-07-04

- Q: ¿Con qué *scope* se almacena y recupera la memoria episódica (AC4)? → A: **Ambos** — cada memoria lleva `project_id` y `user_id` en el payload; la recuperación es **por proyecto** con filtro opcional por usuario.
- Q: ¿La recuperación de memorias está activada por defecto u opt-in (AC4)? → A: **Opt-in** — `AGENT_MEMORY_ENABLED=false` por defecto; se activa por despliegue.
- Q: ¿Valor por defecto de `CONTEXT_BUDGET_RATIO` (AC1)? → A: **0.8** — el último 20% de la ventana queda como zona de seguridad (coincide con la degradación observada); calibrable con EDD sin cambiar la spec.

## 3. Criterios de aceptación

- [ ] **AC1** — *Given* un paso de agente cuyo prompt ensamblado excede el
  presupuesto (`CONTEXT_BUDGET_RATIO × num_ctx` efectivo; **por defecto 0.8**,
  calibrable con los evals de AC6), *When* se construye la
  llamada, *Then* el ensamblador recorta con prioridad **instrucciones >
  borrador vigente > feedback activo > contexto RAG** hasta caber, y registra
  tokens estimados y qué se recortó.
- [ ] **AC2** — *Given* cualquier adapter, *Then* la estimación de tokens y el
  ensamblado presupuestado usan **una utilidad central única** (no lógica
  duplicada por agente), con presupuesto configurable global y por agente.
- [ ] **AC3** — *Given* el bucle Revisor→Redactor con historial acumulado que
  excede el presupuesto, *When* se reinvoca al Redactor, *Then* borradores y
  feedback previos se **compactan en un resumen acotado** (llamada LLM de
  resumen) preservando íntegras las instrucciones de corrección activas, y el
  evento de compactación queda trazado.
- [ ] **AC4** — *Given* una ejecución terminada (o cancelada), *Then* se
  persiste una **memoria episódica** del run (tema, decisiones/HITL, fuentes
  citadas, score final, resumen) en una colección de memoria **separada del
  RAG documental**, con payload `project_id` + `user_id`; la recuperación es
  **por proyecto**, con filtro opcional por usuario; *Given* una nueva ejecución del mismo
  proyecto con la memoria habilitada, *Then* el Investigador recupera las
  memorias relevantes y las aporta como contexto. La memoria es **opt-in**:
  `AGENT_MEMORY_ENABLED=false` por defecto y se activa por despliegue.
- [ ] **AC5** — *Given* un despliegue, *Then* `keep_alive` es configuración
  documentada (default actual `0` con su tradeoff VRAM ↔ caché KV caliente) y
  el uso de contexto por paso (tokens in/out, % de presupuesto, compactaciones)
  se expone en la traza de T9.1 (SPEC-014) y las métricas de T5.2 (SPEC-019).
- [ ] **AC6** — Existen tests que cubren AC1–AC4 sin requerir LLM real
  (estimador determinista + mocks), y un eval EDD (ADR-0006) compara calidad
  con/sin compactación en un caso golden.

## 4. Diseño propuesto

- `platform/context_budget.py` (tras T8.2): `estimate_tokens(text)`
  (aproximación chars/4 configurable [NEEDS CLARIFICATION: ¿aprox. o
  tokenizador real por modelo?]), `assemble(prompt_parts, budget)` con
  prioridades tipadas y reporte de recortes.
- Compactación en `application/use_cases.py`: helper `compact_history(state)`
  invocado antes de reinvocar al Redactor cuando `estimate > budget`; usa el
  LLM configurado con prompt de resumen acotado (~15% del presupuesto).
- Memoria: colección `__memory__` (payload `project_id` + `user_id`, filtrada por
  proyecto — se alinea con el namespace RAG por proyecto de SPEC-013/T8.5);
  escritura al finalizar el grafo; recuperación semántica en el Investigador.
- Config: `CONTEXT_BUDGET_RATIO`, `LLM_KEEP_ALIVE`, `AGENT_MEMORY_ENABLED` (default `false`)
  (+ overrides por agente en frontmatter `.agent.md`).

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| El resumen de compactación pierde instrucciones | Alto | Instrucciones activas nunca se resumen (prioridad 1); eval EDD (AC6) |
| Estimador de tokens impreciso por modelo | Medio | Margen del presupuesto (ratio < 1) absorbe el error; calibrable |
| Coste/latencia de la llamada de resumen | Bajo | Solo bajo presión de contexto; presupuesto de resumen acotado |
| Memoria episódica acumula PII | Medio | Resúmenes sin PII; retención según SPEC-020/AC5 |

## 6. Plan de pruebas

Unit del estimador y del ensamblador (recorte por prioridades, determinista);
integración del bucle con historial sintético grande → compactación disparada
y trazada (LLM mockeado); memoria: persistencia y recuperación round-trip con
Qdrant/local mock; eval EDD golden con/sin compactación.

## 7. Impacto operativo / observabilidad

Nuevas claves de config documentadas en `.env.example`; contadores de
compactaciones y % de presupuesto por paso en traza/métricas; sin migraciones
de BD (la memoria vive en el almacén vectorial).

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E10
  title: "Memoria y contexto de agentes"
  area: area/backend
tasks:
  - id: T10.1
    title: Presupuesto de contexto por paso (estimación central + recorte priorizado)
    sev: high
    depends_on: []
    acceptance: [AC1, AC2]
  - id: T10.2
    title: Compactación del historial del pipeline bajo presión de contexto
    sev: high
    depends_on: [T10.1]
    acceptance: [AC3]
  - id: T10.3
    title: Memoria episódica por proyecto entre ejecuciones
    sev: medium
    depends_on: [T10.2]
    acceptance: [AC4]
  - id: T10.4
    title: Política de caché keep_alive configurable + uso de contexto observable
    sev: low
    depends_on: [T10.1]
    acceptance: [AC5, AC6]
```
