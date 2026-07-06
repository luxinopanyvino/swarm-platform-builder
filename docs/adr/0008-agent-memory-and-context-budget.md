# ADR-0008: Memoria a largo plazo y presupuesto de contexto para los agentes

- **Estado:** Propuesto
- **Fecha:** 2026-07-04
- **Decisores:** Equipo de plataforma
- **Relacionado:** ADR-0005 (arquitectura no-code), ADR-0006 (EDD),
  SPEC-014 (traza por paso), SPEC-021 (spec de esta decisión)

## Contexto

Los agentes del pipeline llaman al LLM con ventanas fijas y pequeñas
(`num_ctx=4096` en redactor/revisor/formateador, `8192` en investigador;
hardcodeadas por adapter) y `keep_alive=0` (se descarga el modelo tras cada
paso para liberar VRAM). El estado del pipeline (borrador + feedback del
Revisor + contexto RAG) **crece monótonamente**: en el bucle Revisor→Redactor
(hasta 3 iteraciones) el prompt puede acercarse al límite de la ventana.

Es un fenómeno conocido que los LLM **degradan antes de agotar la ventana**:
la efectividad cae de forma apreciable cuando la ocupación entra en el último
tramo (~el 20% final), con pérdida de instrucciones y "lost in the middle".
Hoy la plataforma no tiene defensa alguna: no hay conteo de tokens, ni
truncado priorizado, ni compactación del historial, ni memoria entre
ejecuciones (el único almacén es el RAG documental).

El mismo fenómeno aplica a los **agentes de desarrollo** (sesiones de Claude
Code): una sesión larga degrada; la mitigación allí es de **proceso**, no de
código (GOVERNANCE §3.1.5), porque la memoria de largo plazo del proyecto ya
está externalizada en specs/ADRs/bitácoras/issues.

## Decisión

Para los **agentes de producto** (alcance detallado en SPEC-021):

1. **Presupuesto de contexto por paso**: todo prompt se ensambla contra un
   presupuesto `CONTEXT_BUDGET_RATIO × num_ctx` (por defecto ~0,8, es decir,
   nunca entrar en el último ~20% de la ventana). Estimación de tokens
   centralizada; recorte **priorizado** (instrucciones > borrador vigente >
   feedback activo > contexto RAG) y registrado.
2. **Compactación del historial**: cuando el estado acumulado excede el
   presupuesto, se sustituye por un **resumen acotado** generado por el propio
   LLM (equivalente a "vaciar caché" sin perder lo esencial), preservando
   siempre las instrucciones de corrección activas.
3. **Memoria episódica a largo plazo**: al terminar una ejecución se persiste
   un resumen (tema, decisiones, fuentes, score) en una colección de memoria
   separada del RAG documental, recuperable en ejecuciones futuras del mismo
   proyecto.
4. **Política de caché explícita**: `keep_alive` pasa a ser configuración
   documentada (hoy `0` por VRAM; en despliegues con GPU holgada un valor > 0
   conserva la caché KV caliente entre pasos). El uso de contexto por paso se
   expone en la traza de explicabilidad (SPEC-014/T9.1) y las métricas
   (SPEC-019/T5.2).

Para los **agentes de desarrollo**: se codifica en GOVERNANCE §3.1 la
**higiene de contexto** (una tarea por sesión; los artefactos SDD —specs,
bitácoras, issues— son la memoria persistente; compactar/reiniciar sesión al
entrar en el último tramo de la ventana en lugar de degradarse en silencio).

## Alternativas consideradas

- **Solo aumentar `num_ctx`/modelo**: pospone el problema, multiplica VRAM y
  latencia en despliegues on-prem (Ollama), y no resuelve la degradación
  pre-límite ni la falta de memoria entre ejecuciones. Rechazada como única vía.
- **Memoria conversacional completa (todo el historial embebido)**: coste y
  ruido crecientes; la memoria episódica resumida es suficiente para el caso
  editorial. Rechazada.
- **No hacer nada**: la degradación observada en artículos largos/bucles de
  revisión es precisamente el síntoma reportado. Rechazada.
- **Memoria de grafo de conocimiento (Graphiti/Zep) o GraphRAG (Microsoft)**:
  atacan el mismo problema (recuperar solo los hechos relevantes en lugar de
  saturar el prompt), pero exigen infra nueva (grafo Neo4j/FalkorDB) y la
  extracción de entidades/comunidades se paga en llamadas LLM — costosa y de
  calidad dudosa con los modelos locales del stack (llama3.2 1b/3b, mistral 7b).
  **Diferida, no rechazada.** Criterio de activación: si, medida con los evals
  EDD (SPEC-021/AC6), la memoria episódica vectorial se queda corta para
  consultas *relacionales/temporales* (autores↔temas↔fuentes↔decisiones a lo
  largo del tiempo), se abrirá una spec propia para evaluar Graphiti como
  evolución de T10.3.

## Consecuencias

- (+) Prompts siempre dentro de la zona efectiva de la ventana; degradación
  controlada y **medible** (presupuesto + traza).
- (+) Los proyectos acumulan conocimiento entre ejecuciones (memoria episódica)
  sin engordar el RAG documental.
- (−) La compactación introduce una llamada LLM extra cuando se dispara
  (coste/latencia acotados y solo bajo presión de contexto).
- (−) Un resumen puede perder matices; se mitiga priorizando instrucciones
  activas y midiendo con EDD (ADR-0006) la calidad post-compactación.
- (~) La memoria episódica añade superficie de datos → su retención se rige
  por la política de T6.5 (SPEC-020/AC5).
