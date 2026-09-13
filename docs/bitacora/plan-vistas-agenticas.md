# Plan de vistas agénticas y de trazabilidad — E16 a E19

- **Fecha:** 2026-09-13
- **Rama:** `docs/agentic-views-plan`
- **Naturaleza:** autoría de specs (ADR-0007). **Crea** trabajo, no lo resuelve.
- **Entrada:** cuatro maquetas de Fase 1 (dashboard, trazabilidad y logs, subida de
  referencia, generación de paper).

## Qué se midió antes de planificar

Traducir una maqueta a tareas sin mirar el código produce trabajo duplicado y
trabajo imposible a partes iguales. Medido sobre `develop` (5376a30):

| Maqueta | Estado real |
|---|---|
| Dashboard | **No existe.** `App.jsx:162` hace `<Route index element={<Navigate to="articles"/>}>`: entrar en `/dashboard` te deja en el listado |
| Trazabilidad | **El sustrato existe; la vista no.** `agent_run_steps` (T9.1) y `/explain` (T9.2) están; no hay página, ni log transversal, ni exportación, ni hashes |
| Subida de referencia | **A medias.** La subida e indexación funcionan; falta acotarla a un paper, elegir agentes y las notas |
| Generación de paper | **Mayormente existe.** `ExecutionPage.jsx` (508 líneas) ya consume el SSE con `agent_start`, `token`, `await_decision` y `log` |

Y cuatro comprobaciones que salieron vacías: `jsonl`, `anomal`, `fine.tune|LoRA` y
`trace_id` no aparecen en `backend/app/` ni en `frontend/src/`.

## Las cinco cosas que la maqueta esconde y el plan saca a la luz

Esto es lo que justifica que el plan no sea una transcripción de las pantallas.

**1. «MÉTRICAS GLOBALES» en una plataforma multi-tenant es una fuga.** El
aislamiento por proyecto (T8.5) costó construirlo. Una portada que cuente «38
papers» sin filtrar por proyecto filtra información entre proyectos con aspecto de
resumen inocente. AC1 y AC6 de SPEC-028 lo cierran con test de dos proyectos.

**2. «Anomalías detectadas: 0» sin definir qué es una anomalía** no informa:
tranquiliza. Un contador que siempre marca cero es peor que no tenerlo, porque
parece que algo vigila. La traza ya tiene con qué definirlas —`status`,
`iteration`, `latency_ms`, `rag_sources`— así que AC3 las enumera y las cuenta por
separado.

**3. «Integridad · SHA-256» es una afirmación de auditoría.** Un hash por fila
guardado en la misma fila no detecta nada: quien la cambia lo recalcula. Una cadena
sí detecta edición, borrado e inserción — y aun así **no protege frente a quien
pueda reescribir la base entera**. SPEC-029 implementa la cadena y obliga (AC6) a
decir ese límite **en la interfaz**, no solo en la documentación: un sello que
promete de más convierte una duda sana en confianza infundada.

**4. «Agentes participantes» no es una lista de casillas.** La forma del pipeline
es un dato (T8.3) y se **valida al cargar** para que el error salga al principio.
Un subconjunto por ejecución es una variante del `GraphSpec`: si no pasa por la
misma validación, quitar el Revisor deja el bucle Revisor→Redactor apuntando a un
nodo inexistente, y eso revienta en el minuto ocho — justo lo que T8.4 evitaba.

**5. «Redactor 40 %» no se puede calcular hoy.** El pipeline emite `agent_start` y
`token`, no unidades de trabajo. Un porcentaje derivado de tokens o de tiempo tiene
la precisión de un dato y el valor de una suposición, y la gente decide con él
(«le falta poco, espero»). AC5 de SPEC-030 lo **prohíbe**: o el agente emite
unidades reales, o se muestra indeterminado.

## Y la que no es un detalle: fine-tune

La maqueta pone «RAG» y «Fine-tune — entrenamiento local» como dos radios, uno
encima del otro. La diferencia no es de esfuerzo, es de naturaleza:

> **RAG se puede deshacer; un fine-tune no.** Borrar un documento de la biblioteca
> elimina su influencia en la siguiente recuperación. Si ese documento entró en un
> entrenamiento, su contenido queda dentro de los pesos.

Eso choca con [data-retention.md](../governance/data-retention.md) y con cualquier
petición de supresión. Más: un modelo no lleva cabecera `X-Project-Id`, así que el
aislamiento de T8.5 no se hereda solo; y entrenar compite por la VRAM con la que el
pipeline ya pelea (`keep_alive=0`, `num_ctx` fijo).

Por eso **SPEC-031 queda en `Draft`**, con seis preguntas abiertas y sin criterios
de aceptación. Las specs en `Draft` no generan issues: es la salvaguarda de que
nadie se ponga a implementar una decisión que no está tomada. Hay un test que falla
si sale de `Draft`, para que salir sea un acto deliberado con el ADR delante.

## Qué se entrega

| Archivo | Épica | Estado |
|---|---|---|
| `SPEC-028-dashboard-swarm-status.md` | **E16** `area/observability` | Ready · 7 AC · 6 tareas |
| `SPEC-029-traceability-view-and-integrity.md` | **E17** `area/observability` | Ready · 7 AC · 6 tareas |
| `SPEC-030-reference-input-and-run-control.md` | **E18** `area/ux` | Ready · 7 AC · 6 tareas |
| `SPEC-031-format-learning-finetune.md` | **E19** `area/backend` | **Draft** · sin AC · 2 tareas no sembradas |

Más las secciones E16–E19 del backlog y `backend/tests/test_spec_plan_coherence.py`.

## Sobre los tests

El fichero nuevo comprueba tres invariantes que `validate_specs.py` no mira, **en
todas las specs y no solo en las de este plan**: que el prefijo de cada tarea case
con su épica, que toda dependencia tenga destino —global, porque cruzan specs:
`T9.1` depende de `T5.1`, que vive en SPEC-019— y que una spec nueva no pise una
épica existente.

Los genéricos que había duplicado en `test_qa_area_registration.py` se han
retirado de ahí: dos sitios probando lo mismo es exactamente lo que este repo evita.

## Verificación

- `pytest tests/test_spec_plan_coherence.py tests/test_qa_area_registration.py` →
  27 pasan, 1 se salta (SPEC-031 en `Draft` no declara AC todavía).
- Suite backend completa en verde (ver PR).
- `scripts/validate_specs.py` → OK.
- **Mutación** (6 mutaciones, las 6 detectadas): épica nueva que pisa una
  existente; tarea con prefijo de otra épica; dependencia sin destino; un AC que
  ninguna tarea reclama; SPEC-031 saliendo de `Draft`; una spec sin entrada en el
  backlog.

La cuarta mutación falló a la primera —quité `AC5` de `T18.6` y el test siguió
verde— y **el test tenía razón**: `AC5` también lo reclama `T18.4`, así que no
quedaba huérfano. Se repitió con `AC7` de SPEC-028, que solo reclama una tarea, y
entonces sí cayó. Una mutación que no cambia el hecho que se prueba no prueba nada.

## Un hallazgo ajeno a este plan

**SPEC-022 tiene su `AC6` sin ninguna tarea que lo reclame.** No se toca aquí
—arreglar la spec de otra épica no es asunto de esta— y tampoco se esconde tras una
excepción en el test: el caso está acotado a las specs de este plan y el hallazgo
queda escrito para que se decida aparte.

## Lo que queda fuera

- **Nada se ha sembrado.** `/sdd-sync --apply` crea los issues; no se ejecuta sin
  decisión explícita.
- **Las tres specs `Ready` no han pasado `/speckit-clarify` ni
  `/speckit-checklist`**, igual que las de E14/E15. La DoR lo pide como recomendado
  y no bloqueante (ADR-0007); aquí pesa más que en el plan anterior, porque estas
  tres describen interfaz y la interfaz es donde más barato sale aclarar antes.
- **El orden entre épicas no está decidido.** E17 depende de que la traza siga
  siendo la fuente (lo es), E16 se apoya en las mismas consultas, y E18 toca el
  motor. Si hay que elegir una, E17 es la que convierte datos que ya existen en algo
  utilizable sin tocar el pipeline.
