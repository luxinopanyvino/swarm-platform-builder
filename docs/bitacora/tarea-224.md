# Tarea #224 — T9.2 Endpoint `/explain` + panel «Por qué este resultado»

## 2026-09-04 — Completada ✅

- **Rama:** `feat/224-explain-endpoint`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #224`)
- **Spec/ADR:** SPEC-014, Épica E9, ADR-0006. Criterio vinculante: **AC2**.
- **Dependencias:** T9.1 (#221), ya integrada — esta tarea es la que hace visible
  lo que aquella persistió.

## Qué se hizo

`GET /api/v1/agents/{article_id}/explain` y el panel que lo lee, montado bajo el
cuerpo del artículo en el detalle. Devuelve los pasos con su modelo, sus
parámetros, lo que recuperaron del RAG, lo que decidieron y lo que costaron; más
las fuentes agregadas y los totales de la ejecución.

Sin esto, T9.1 era un dato persistido que nadie podía ver, y un dato que nadie ve
no explica nada.

## El problema, que no era «serializar la tabla»

**Un artículo se puede reejecutar.** Entonces su traza tiene los pasos de varias
ejecuciones en la misma tabla, y devolverlos todos ordenados por `step_index` los
entrelaza: dos ejecuciones tienen las dos un paso 0, un paso 1… El panel contaría
una historia que no ocurrió —el revisor aprobando un borrador que ya no existe— y
lo haría de forma perfectamente creíble, que es lo peor que puede pasarle a una
herramienta cuyo propósito es explicar.

Lo que separa las ejecuciones es que **`step_index` vuelve a 0**: el orquestador
lo reinicia en cada ejecución nueva. Una reanudación (`resume`) no reinicia
—continúa desde el checkpoint de LangGraph—, así que sigue la numeración y
aparece como lo que es: la misma ejecución terminada en un segundo intento.

Por defecto se explica **la última**, que es la que produjo el texto que se está
leyendo y la pregunta que trae a alguien al panel; `?scope=all` las devuelve
todas para auditar. El panel dice cuántas hay, para que nadie crea que lo que ve
es todo lo que pasó.

## Decisiones documentadas

- **No se agrupa por `run_id`.** No es lo que parece: `log_run_start` mina uno
  **por paso**, no por ejecución. Ni por `correlation_id`, que puede faltar.
- **Orden cronológico** (`created_at`), no por `step_index`: es el orden en el que
  ocurrieron, y es lo único correcto cuando hay varias ejecuciones. `step_index`
  desempata dos pasos con la misma marca de tiempo, que en SQLite es posible.
- **Las fuentes se agregan por documento a través de los pasos.** La traza las
  guarda por paso, que es lo correcto para explicar un paso; pero la pregunta del
  panel suele ser la otra —«¿en qué documentos se apoya esto?»—, y reconstruirlo
  en el cliente lo haría distinto en cada cliente. Se añade `used_by`: distingue
  la fuente que solo vio el investigador de la que además usó el redactor.
- **`available` distingue «no se ha ejecutado» de «la traza se purgó».** Son dos
  vacíos distintos y solo uno tiene arreglo; sin el campo, el panel diría lo mismo
  en los dos casos.
- **Mismo control de acceso que `/runs`**: la unidad de acceso es el artículo, y
  la traza no dice nada que su dueño no pueda ver ya. La cabecera `X-Project-Id`
  **no** se exige —ningún endpoint de artículo la pide en este repo, y volverla
  obligatoria solo aquí es una trampa para el siguiente cliente— pero **si viene
  se comprueba**: un artículo de otro proyecto responde 404, no 403, porque la
  respuesta no debe distinguir «es de otro proyecto» de «no existe». Eso es
  exactamente para lo que existe `get_optional_project_context`.
- **El panel vive en `platform/`, no en el proyecto.** La explicabilidad es del
  motor: cualquier proyecto que ejecute un pipeline tiene pasos, fuentes y
  decisiones. Lo único del proyecto —cómo se llama y de qué color es cada
  agente— se pregunta al registro `agentCatalog` (T8.6); no se importa.
- **Los dos scores no se pintan igual.** El del revisor es una aprobación de 0 a
  100; el de una fuente, una similitud coseno de 0 a 1. Enseñar «0,91» y «91» con
  el mismo formato invita a leerlos como lo mismo, así que la similitud va como
  porcentaje y con la palabra «similitud» al lado.
- **La barra de similitud es una ayuda, no el dato.** El porcentaje va escrito:
  el color por sí solo no comunica (viene de T7.2).
- **El panel debajo del cuerpo, no en la barra lateral.** La traza es contenido
  ancho —línea de tiempo, fuentes, comentarios del revisor— y en 280 px no se lee.
- **La carga se inyecta** (`load`, por defecto la API real). Es lo que permite
  conducir el panel en un navegador de verdad, que es la única forma de comprobar
  lo que promete.

## Lo que encontró el navegador

**El detalle se veía con `aria-expanded="false"`.** El contenedor llevaba
`hidden={!abierto}` y, en la misma etiqueta, un `display: flex` en línea. El
`display: none` que `hidden` trae de la hoja del navegador lo pisa cualquier
`display` en línea, así que el atributo no ocultaba nada: el botón decía
«cerrado» y el detalle estaba abierto. Leyendo el código se ve un componente
correcto; hizo falta abrirlo en Chromium. El `display` sale ahora de `abierto`.

**Y un cambio de alcance que falla enseñaba el otro.** `AsyncState` mantiene los
datos en pantalla cuando falla una recarga —para un refresco es lo correcto: tirar
una lista legible para enseñar un error sería peor—, pero al cambiar de alcance lo
que queda es la respuesta a **otra** pregunta. El panel solo pinta la traza cuyo
`scope` coincide con el pedido; el botón, en cambio, se decide con lo último que
se sabe del artículo, porque esconderlo al fallar deja a quien lo pulsó sin manera
de volver.

## Test nuevo

`backend/tests/test_explain_endpoint.py` (16 casos) y
`backend/tests/test_explain_panel.py` (13, de los cuales 9 en navegador).

- **Agrupar ejecuciones**, como funciones puras sin base de datos: dos ejecuciones
  no se mezclan, una reanudación es una sola, las fuentes se agregan quedándose el
  mejor score y uniendo fragmentos, una fuente sin `doc_id` no entra, y un score
  no numérico —`rag_sources` es JSON— no tumba la lectura de toda la traza.
- **Contra la API**: la traza llega entera con fuentes, score y decisión; por
  defecto se explica la última ejecución y `scope=all` las da todas; un `scope`
  inventado se rechaza; un artículo sin traza lo dice en vez de parecer vacío; la
  traza de otra persona no se lee; sin autenticar tampoco; y con otro proyecto
  activo el artículo responde 404.
- **Contra el pipeline real**: se ejecuta el orquestador **dos veces** y se mira
  qué devuelve el endpoint. La separación se apoya en cómo numera otro módulo, y
  leerlo no basta: si algún día el orquestador numera de otra forma, cae este test
  y no el panel en producción, que es donde no se vería.
- **En Chromium** (9 casos), conduciendo el componente real: que se pinta un paso
  por agente con el nombre del catálogo y no con el identificador crudo; que el
  detalle se abre y se cierra —y ahí saltó el fallo del `display` en línea—; que
  enseña modelo, parámetros y lo recuperado; que la decisión del revisor se lee
  con su porqué; que los dos scores no se leen como el mismo número; que la vuelta
  del bucle se indica; que se avisa de que hay más ejecuciones; que **un fallo de
  carga no se disfraza de «sin traza»**, la mentira que T7.3 fue a arreglar; y que
  un cambio de alcance que falla no enseña el alcance anterior.

Verificado por mutación: devolver todas las ejecuciones mezcladas, quitar la
comprobación de propiedad, quitar el cruce con el proyecto activo, dejar
`available` siempre a `true` y quedarse el peor score al agregar. Cada mutación
tumba su test.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → VERIFICACION_SUITE

npm run build && npm run build:public     # → ambos OK
python3 scripts/check_design_tokens.py    # → [OK]
python3 scripts/check_async_states.py     # → [OK]
python3 scripts/validate_specs.py         # → [OK]
```

## Definition of Done

- [x] **AC2** — el endpoint devuelve la traza completa estructurada y el panel la
  muestra con fuentes, score y decisiones por paso.
- [x] Tests que cubren el cambio, en verde (29 nuevos: 16 del endpoint, 13 del panel).
- [x] Docs: SPEC-014 anotada. Sin cambios de esquema ni de retención: T9.2 solo
  lee lo que T9.1 ya guardaba, con su misma ventana de 90 días.
- [x] Sin secretos ni PII nueva en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **El panel enseña `output_text` recortado a 4.000 caracteres**, que es lo que
  guarda T9.1. Para un artículo largo, el texto del redactor aparece truncado; no
  es un fallo del panel, es la política de la traza (data-retention §«resúmenes
  recortados»). Si alguna vez molesta, la decisión es sobre lo que se guarda.
- **Los tokens quedan a 0 cuando el proveedor no los devuelve** (el camino de
  streaming de OpenAI no los pide, ver `llm.py`). El panel enseñará 0 tokens con
  toda naturalidad; documentarlo en el propio panel es candidato a T9.4.
- **`GET /explain` no pagina.** Un artículo con muchas reejecuciones y `scope=all`
  devuelve todo de golpe. Con la retención de 90 días y pipelines de cinco pasos
  el volumen es pequeño, pero es lo primero que habría que mirar si alguien
  automatiza reejecuciones.
- **E9 queda con T9.4 (#225) y T9.5 (#226)**; T9.6 (#223) es la gobernanza de EDD.
