# Harness EDD — comportamiento de los agentes

SPEC-014 (épica E9) · ADR-0006 · tarea T9.3 (#222)

Evalúa **los agentes de esta plataforma**: sus perfiles, sus prompts y el modelo
que cada uno usa con el `LLM_PROVIDER` activo. No compara modelos *foundation* —
eso es `evals/model_benchmark/` (SPEC-025), y es un esfuerzo distinto con otra
pregunta.

## Por qué

Cambiar el `prompt_template`, el `model` o la `temperature` de un agente puede
**degradar la calidad en silencio**. Un artículo que cita fuentes inventadas se
lee igual de bien que uno que cita fuentes reales; un formateador que pierde las
citas numeradas de IEEE sigue produciendo texto correcto. Sin una medida, la
regresión aparece semanas después y ya nadie sabe qué la causó.

## Cómo se ejecuta

```bash
# Desde backend/. Reproducible y sin servicios externos.
python -m evals.agent_behavior.runner --dataset redactor-smoke --mode replay

# Contra el agente real, con el modelo y los parámetros de la plataforma.
python -m evals.agent_behavior.runner --dataset redactor-smoke --mode live

# Guardar el informe (JSON para máquinas, markdown para personas).
python -m evals.agent_behavior.runner --dataset redactor-smoke --out evals/results
```

Sale con **código 1** si algún caso falla, para que un gate pueda usarlo tal cual.

## Los dos modos, y por qué son dos

AC3 pide un informe **reproducible** «sin depender de servicios externos no
declarados». Son dos exigencias que tiran en direcciones opuestas: medir el
comportamiento real obliga a llamar al modelo, y un modelo generativo ni da dos
veces lo mismo ni está disponible en la CI.

| Modo | Qué mide | Determinista |
|---|---|---|
| `live` | El agente real, con su modelo y sus parámetros. **Mide el comportamiento.** | No |
| `replay` | Las métricas y el harness, sobre salidas grabadas. **No evalúa al modelo.** | Sí |

Confundirlos sería lo peor que le puede pasar a este harness —un `replay`
presentado como prueba de que el agente va bien—, así que el modo aparece en el
informe, en el nombre del fichero y con un aviso en la cabecera del markdown.

En `live` el informe no es byte a byte repetible, y no pretende serlo: lo que lo
hace comparable es que registra **con qué se hizo** (modelo, proveedor, versión y
hash del dataset, commit).

## Datasets

Un `.jsonl`: cabecera con `id` y `version`, y un caso por línea. JSONL porque un
dataset crece por líneas, y así el diff de una PR enseña qué caso se añadió.

| Dataset | Para qué |
|---|---|
| `redactor-smoke` | Pasa. Comprueba que el harness funciona de extremo a extremo. |
| `redactor-regressions` | **Falla a propósito**: un caso por regresión detectable. Documentación ejecutable de qué se mide. |

Los conjuntos *golden* de verdad llegan con **T9.4 (#225)**.

Campos de un caso:

```jsonc
{
  "id": "cita-fiel",
  "agent": "redactor",
  "input": { /* claves del AgentState que el agente lee */ },
  "corpus": [ /* documentos que existen de verdad: la referencia de las citas */ ],
  "expect": {
    "min_citations": 1,
    "min_citation_fidelity": 100,
    "scientific_format": "apa",
    "required_sections": ["Introducción"],
    "max_tokens_out": 800
  },
  "recorded_output": "…",          // para --mode replay
  "recorded_usage": {"tokens_in": 320, "tokens_out": 210}
}
```

### Un caso que use RAG tiene que declarar su proyecto

En `live`, el estado del agente se construye a partir de `input`. Si el agente
recupera documentos, el `input` debe traer `project_id`: el nombre de la colección
de Qdrant **se deriva de él** (T8.5), y sin él la capacidad de RAG avisa y cae al
espacio heredado, que en una evaluación no es lo que se quiere medir.

## Métricas

Todas puntúan de **0 a 100**. La escala única hace comparables cosas de
naturalezas distintas y permite declarar umbrales (T9.5) sin traducir unidades.

| Métrica | Qué comprueba | Se salta cuando |
|---|---|---|
| `citation_fidelity` | Que cada `[Fuente: X]` exista en el corpus del caso. | El caso no trae corpus. |
| `format_compliance` | Que aparezca el estilo de cita pedido y las secciones exigidas. | El caso no declara ninguno. |
| `budget` | Margen frente al presupuesto de tokens y latencia. | El caso no declara presupuesto. |

Una métrica que no aplica **se salta con motivo**, no puntúa 100: aprobar por no
haber mirado es mentir con buena nota.

Añadir una métrica es añadir un módulo en `metrics/` que se registre; el runner no
se toca.

## Qué **no** hace todavía

- Las métricas **asistidas** (calibración del score del revisor, coherencia con
  juez) son T9.4.
- El **gate en CI** con umbrales por agente es T9.5.
