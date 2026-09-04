# Tarea #221 — T9.1 Traza de explicabilidad por paso (`agent_run_steps`)

## 2026-09-04 — Completada ✅

- **Rama:** `feat/221-explainability-trace`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #221`)
- **Spec/ADR:** SPEC-014, Épica E9, ADR-0006. Criterio vinculante: **AC1**.
- **Dependencias:** T5.1 (logging estructurado, SPEC-019), ya integrada — la traza
  reutiliza su `correlation_id`. Abre E9 y desbloquea T9.2 (#224).

## Qué se hizo

Tabla **`agent_run_steps`** (migración `0004`), una fila por paso de agente, que
el orquestador escribe al cerrar cada nodo. Con lo que AC1 pide: agente, modelo y
parámetros, resumen de entrada y salida, fuentes RAG recuperadas con `doc_id`,
`chunk_ids` y score, tokens in/out, latencia, y decisión + *rationale* cuando el
paso decide algo.

## El problema, y por qué no bastaba con «añadir una tabla»

`agent_runs` ya registraba **que** un agente corrió, con su entrada y su salida.
Lo que no registraba es **por qué** salió lo que salió. Y tres de los datos que
hacen falta para contestarlo no están donde se escribiría el registro:

- **Los tokens** solo los conoce el proveedor del LLM, dentro de `llm.py`, que ni
  siquiera sabe qué agente está corriendo.
- **Las fuentes RAG** solo las conoce la capacidad de RAG. El agente que la llama
  se queda con el texto ya montado, y las citas que acaban en el artículo son una
  **elaboración posterior**: no son lo que se recuperó.
- **La decisión** la produce el agente y viaja en su salida.

Se podían pasar por parámetro hasta el orquestador, pero eso significa cambiar la
firma de todo lo que hay en medio y, sobre todo, que un agente nuevo **no aparezca
en la traza** hasta que alguien se acuerde de instrumentarlo. Es el fallo que se
arregla a sí mismo mal: silencioso y creciente.

Se recogen con **variables de contexto** (`platform/explainability.py`), el mismo
patrón que `current_agent_ctx` para las métricas de T5.2: quien produce el dato lo
anota donde está, y el orquestador lo recoge al cerrar el paso. Un agente nuevo
queda trazado sin tocarlo.

## Lo que apareció al conectarlo

**El respaldo local no anotaba nada.** `_fetch_agent_results` es el camino que se
usa **sin Qdrant** —desarrollo y cualquier instalación que no lo levante—, y sus
salidas se quedaban fuera de la anotación. Habría sido una traza sin fuentes
justo en el entorno donde más se depura, y sin ningún síntoma. Se anota también
ahí, usando el índice del fragmento como `chunk_id`.

**Y `semantic_search_results` descartaba el identificador del punto.** Devolvía
`doc_id` pero no el id de Qdrant, así que la traza podía decir *de qué documento*
salía algo pero no *qué fragmento*. AC1 pide `chunk_ids` en plural por algo.

## Decisiones documentadas

- **También se traza el paso que falla.** AC1 dice «cuando termina **o se
  cancela**», y un paso que revienta es justo el que hay que explicar. Se guarda
  su error y los tokens consumidos antes de caer, que son coste real.
- **La traza no puede tumbar el pipeline… pero tampoco callarse.** `log_run_step`
  usa su propia sesión y traga la excepción, y registra un `WARNING`. Una traza
  que se pierde en silencio es peor que no tenerla: da confianza infundada.
- **Un paso ≠ un agente.** El bucle revisor→redactor hace que el mismo agente
  aparezca varias veces; `step_index` e `iteration` los distinguen.
- **Se guardan resúmenes, no prompts.** El `input_digest` es un resumen legible
  (título, palabras clave, tamaño de la investigación y del borrador, vuelta del
  bucle) y las salidas se recortan a 4.000 caracteres. La traza explica una
  ejecución; no es un segundo almacén del artículo, que ya está en `articles`.
- **Las fuentes se agrupan por documento** con sus `chunk_ids` y el **mejor**
  score. La pregunta que responde la traza es «¿de qué documentos salió esto?»; una
  lista de fragmentos sueltos obliga a reconstruirlo a mano.
- **`decision` es `NULL` en los pasos que no deciden**, en vez de un diccionario
  vacío: dice más.
- **`run_id` es `SET NULL` y `article_id` es `CASCADE`.** Si la retención purga un
  `agent_run`, la traza sigue explicando lo que pasó hasta que le toque a ella;
  pero sin el artículo, la explicación de cómo se generó no describe nada.
- **Retención de 90 días, la misma que `agent_runs`.** Describe las mismas
  ejecuciones con el mismo detalle: darle una ventana más larga alargaría por la
  puerta de atrás la retención de lo que el usuario escribió.

## Test nuevo

`backend/tests/test_explainability_trace.py` (18 casos):

- **El recolector**: los tokens se suman entre llamadas (el redactor amplía el
  borrador si se queda corto); las fuentes se agrupan por documento con el mejor
  score; un fragmento repetido no duplica su `chunk_id`; anotar **fuera** de un
  paso no revienta (el RAG se usa también sin pipeline); y dos ejecuciones
  simultáneas no se mezclan.
- **De extremo a extremo**: una ejecución de tres agentes deja un paso por agente
  con sus tokens, su latencia, su resumen de entrada y sus fuentes; los tokens **no
  se arrastran** de un paso al siguiente; un paso que falla se traza con su error;
  y el bucle de revisión deja un paso por vuelta, con `iteration` distinto.
- **Las dos costuras**, que son lo que hace que esto funcione sin tocar los
  agentes: que `_record_usage` alimente la traza, y que la capacidad de RAG lo
  haga **también sin Qdrant**.
- **Retención**: la ventana coincide con la de `agent_runs`, está documentada, y
  la purga borra lo vencido.

Verificado **por mutación**, y el primer intento lo suspendió: quitando la llamada
de `llm.py` los tests seguían en verde, porque los agentes de prueba anotaban los
tokens ellos mismos. De ahí salieron los dos casos de las costuras — y con ellos
el hallazgo del respaldo local sin anotar. Ahora cada mutación tumba su test.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 675 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

alembic upgrade head && alembic check     # → "No new upgrade operations detected."
npm run build && npm run build:public     # → ambos OK
python3 scripts/validate_specs.py         # → [OK]
```

## Definition of Done

- [x] **AC1** — traza persistida por paso con todo lo que enumera el criterio,
  incluidos los pasos que fallan.
- [x] Tests que cubren el cambio, en verde (18 nuevos; 675 en la suite).
- [x] Esquema por migración Alembic (`0004`), con `alembic check` limpio.
- [x] Docs: SPEC-014 anotada, `CLAUDE.md`, y **la política de retención
  actualizada** — es una tabla que acumula rastro y hay un test que lo exige.
- [x] Sin secretos ni PII nueva; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **T9.2 (#224) queda desbloqueada**: `GET /agents/{article_id}/explain` y el panel
  «Por qué este resultado». El DTO `AgentRunStepResponse` ya está escrito para eso.
  Ojo al entregarlo: la traza incluye texto del artículo, así que el endpoint tiene
  que ir con el mismo control de acceso y con la cabecera `X-Project-Id` de T8.5.
- **Los tokens dependen de que el proveedor los devuelva.** Ollama y OpenAI los
  traen; el camino de streaming de OpenAI no los pide a propósito (ver el
  comentario en `llm.py`), así que ahí `tokens_*` quedan a 0. No se cambia aquí:
  tocarlo es una decisión sobre el consumo de la API, no sobre la traza.
- **La traza es el sustrato de T9.3–T9.5** (harness EDD, datasets golden y gate en
  CI): las métricas de fidelidad de citas y de presupuesto de tokens salen
  directamente de estas columnas.
