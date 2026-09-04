# Tarea #225 — T9.4 Conjuntos *golden* y métricas de comportamiento

## 2026-09-04 — Completada ✅

- **Rama:** `feat/225-golden-datasets`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #225`)
- **Spec/ADR:** SPEC-014, Épica E9, ADR-0006. Criterio vinculante: **AC4**.
- **Dependencias:** T9.3 (#222), ya integrada. Desbloquea T9.5 (#226), que es la
  última de E9 junto con T9.6 (#223).

## Qué se hizo

Los conjuntos de referencia que faltaban y las **dos métricas asistidas** de AC4.
T9.3 dejó tres métricas deterministas y dos datasets de ejemplo; aquí llegan los
`<agente>-golden` de los cuatro agentes evaluables, sus `<agente>-regressions`, y
las dos medidas que no se pueden calcular con una expresión regular: calibración
del revisor y coherencia.

## Las dos métricas nuevas, y por qué eran las difíciles

**`reviewer_calibration`.** El revisor no escribe: **decide**. Su score cruza el
umbral de 80 que hace volver el borrador al redactor. Que sea un número no lo
hace objetivo: un revisor que aprueba todo con 85 y otro que suspende todo con 70
producen los dos una cifra perfectamente formada, y los dos rompen el pipeline —el
primero deja pasar basura, el segundo agota el bucle de tres vueltas en textos
buenos—. La métrica mide la distancia a una referencia humana y, **por separado,
el lado del umbral**: un 78 frente a un 82 son cuatro puntos y una decisión
distinta, así que cruzarlo se penaliza aunque la distancia sea corta.

**`coherence`.** Es la única que caza un texto que cita fuentes que existen,
cumple APA, cabe en el presupuesto y **se contradice a sí mismo** entre la
metodología y los resultados. Las tres deterministas lo aprueban. Hay un caso en
`redactor-regressions` que es exactamente eso, para que la métrica tenga su prueba.

## Decisiones documentadas

- **El juez lo pide el runner, no la métrica.** Si la métrica llamara al modelo,
  `replay` dejaría de ser reproducible y la CI de T9.5 pasaría a depender de que
  haya un modelo levantado. Se pide donde se sabe el modo, y las métricas siguen
  siendo funciones puras sobre lo ya obtenido: el mismo reparto que en T9.1, donde
  quien conoce el dato lo anota y quien lo consume solo lo lee.
- **En `replay` no se llama a nadie**, y sin veredicto grabado la métrica **se
  salta con motivo**. Ni 100 —aprobar por no haber mirado, la mentira con buena
  nota— ni 0 —hacer fallar el gate por una evaluación que no se hizo—.
- **Rúbrica fija, versionada y `temperature=0`** (SPEC §5). Un juez que cambia de
  criterio entre ejecuciones convierte el gate en un generador de rojos
  aleatorios: la métrica dejaría de medir al agente para medir al juez. La rúbrica
  prohíbe explícitamente premiar extensión, estilo o formato — eso ya lo miden
  otras métricas, y un juez que las mezcla hace incomparables los números.
- **Un conjunto *golden* pasa entero.** Es lo que lo hace utilizable como línea
  base: con un caso que falla a propósito dentro, T9.5 no podría distinguir «ha
  regresado» de «siempre fue rojo». Las degradaciones van a `*-regressions`, que
  es la separación que T9.3 ya había establecido y que el primer borrador de esta
  tarea rompió.
- **Los datasets declaran `provenance`, y el informe lo repite.** Un `replay`
  sobre salidas escritas a mano evalúa **la métrica**, no lo que hace el modelo
  con ese caso. Es evidencia de otra cosa, y callarlo dejaría leer las dos como si
  fueran lo mismo — el mismo criterio que el aviso de `replay` de T9.3.
- **El publicador no tiene conjunto.** Publica: no genera texto ni decide, así que
  no hay comportamiento probabilístico que medir. Inventarle un dataset sería
  llenar el informe de métricas saltadas.
- **La decisión del revisor se lee con el `decision_of` de T9.1**, no con un
  lector propio: si el revisor cambia de forma, cambia en un sitio.

## El dispatcher no aceptaba `temperature`

SPEC §5 exige el juez a `temperature=0`, y al ir a pasarla apareció que
`call_llm` **no tiene ese parámetro**: los perfiles de agente guardan una
`temperature` en BD (`agents_seed.py` fija una por agente) que nunca llega a
ningún proveedor. Se añade al dispatcher como opcional y se reenvía a los tres
caminos —Anthropic, OpenAI y Ollama— **solo cuando no es `None`**, así que ningún
agente cambia de comportamiento por esto.

Lo que **no** se hace aquí es conectar la `temperature` de los perfiles: eso
cambia cómo generan los cinco agentes y merece su propia tarea, no ir de polizón
en una de evaluación. Queda anotado en seguimiento.

## Test nuevo

`backend/tests/test_edd_golden.py` (38 casos) y dos en `test_llm_anthropic.py`.

- **Los conjuntos**: cada agente evaluable tiene el suyo, el `golden` **pasa
  entero** (si no, no sirve de gate) y el de regresiones **falla**; todos declaran
  su procedencia; y el informe avisa cuando las salidas no son grabadas.
- **Calibración**: un score cercano puntúa alto; cruzar el umbral falla aunque la
  distancia sea corta —y puntúa por debajo de la misma distancia sin cruzarlo—; se
  detectan el revisor complaciente y el severo; acertar el lado con una desviación
  grande no basta; y sin decisión la métrica **falla** en vez de saltarse, porque
  que el revisor no devuelva score *es* el fallo.
- **Coherencia y juez**: el veredicto se puntúa con su motivo; un texto que se
  contradice no pasa; sin veredicto se salta con motivo; **en `replay` no se llama
  al modelo** (con el `call_llm` parcheado para reventar si alguien lo intenta);
  el juez llama con `temperature=0`; no juzga una salida vacía; un veredicto sin
  JSON o con score no numérico se rechaza; el score se recorta al rango; el JSON
  envuelto en prosa se parsea; y un juez que falla no tumba el caso pero **avisa**.
- **El revisor**: que un agente que decide y no escribe sea evaluable de extremo a
  extremo, y que su conjunto cubra los dos lados del umbral —uno que solo traiga
  aprobados no detecta a un revisor complaciente—.
- **El dispatcher**: que `temperature` llegue al proveedor cuando se pide y **no
  se envíe cuando no**, que es lo que mantiene intacto el comportamiento actual.

Verificado por mutación: ignorar el lado del umbral en la calibración, aprobar la
coherencia sin veredicto, dejar de propagar la decisión al resultado, quitar la
`temperature=0` del juez y usar el juez de plataforma en `replay`. Cada mutación
tumba su test.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 811 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

# Los ocho datasets, con el código de salida que deben tener:
for d in {investigador,redactor,revisor,formateador}-golden;      → exit 0
for d in {investigador,redactor,revisor,formateador}-regressions; → exit 1

python3 scripts/validate_specs.py         # → [OK]
```

## Definition of Done

- [x] **AC4** — conjuntos *golden* versionados y las cinco métricas de
  comportamiento que enumera el criterio.
- [x] Tests que cubren el cambio, en verde (40 nuevos).
- [x] Docs: SPEC-014 anotada, `README.md` del harness y `CLAUDE.md`.
- [x] Sin secretos ni PII en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **Los conjuntos son `handwritten` y hay que regrabarlos.** No hay Ollama ni
  clave de proveedor en el entorno donde se construyeron, así que las salidas se
  escribieron a mano para fijar qué mide cada métrica. Un verde dice que **la
  métrica** funciona, no que el agente se comporte así. Regrabarlos con
  `--mode live` contra el modelo de la plataforma —y pasar `provenance` a
  `recorded`— es el paso previo a endurecer el gate de T9.5, y con ello vienen las
  referencias reales del revisor, que hoy son las que un humano estimó.
- **T9.5 (#226)** tiene ya lo que necesita: `<agente>-golden` como línea base, el
  JSON con `scores` y `passed`, y el código de salida. SPEC §5 pide arrancar en
  modo **aviso** y endurecer tras fijar la línea base — con conjuntos escritos a
  mano, endurecer antes sería fijar una línea base ficticia.
- **La `temperature` de los perfiles sigue sin llegar al modelo.** El dispatcher ya
  la acepta; conectarla desde `agent_settings` cambia cómo generan los cinco
  agentes y necesita su propia tarea y su propia verificación.
- **La rúbrica del juez está versionada** (`RUBRICA_VERSION`). Si se toca, hay que
  subir la versión de los datasets que la usan: los números anteriores dejan de
  ser comparables.
