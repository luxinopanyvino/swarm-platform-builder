# Tarea #209 — T8.3 Adapters de AlejandrIA como composición de capacidades

## 2026-09-03 — Completada ✅

- **Rama:** `feat/209-capability-composition`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #209`)
- **Spec/ADR:** SPEC-013, Épica E8, ADR-0005. Criterios: **AC8** (cumplido) y la
  mitad de **AC5** que corresponde a esta tarea.
- **Dependencias:** T8.2 (#239), ya integrada.

## Lo que había

El orquestador conocía a AlejandrIA de tres formas distintas, todas escritas
dentro del motor:

```python
agents_map = { "investigador": …, "redactor": …, "revisor": …, … }   # (1)
if "revisor" in nodes_to_add: nodes_to_add.add("redactor")           # (2)
if node_name == "revisor": workflow.add_conditional_edges(…)         # (3)
```

Más el enrutado, con el umbral (`< 80`), el máximo de vueltas (`3`) y el destino
del rechazo (`"redactor"`) como constantes de módulo.

Mientras el único proyecto sea AlejandrIA, esto funciona. En una plataforma donde
cada proyecto trae sus agentes, el problema no es que falle: es que **no falla**.
Un proyecto cuyo revisor se llame `qa` compila un grafo perfectamente válido, sin
bucle de revisión y sin ningún aviso. La revisión simplemente no ocurre.

Y (1) es el sitio que habría que editar para dar de alta un agente nuevo — es
decir, no había alta de agentes.

## Lo que se hizo

**El enrutado es un dato.** `platform/engine/routing.py` define `ReviewLoop`
—revisor, destino del rechazo, umbral, máximo de vueltas y a dónde volver si
alguien sube una fuente— y fabrica el enrutador a partir de él. El motor no
menciona a `revisor` ni a `redactor` en ningún sitio.

**La forma del grafo es un dato.** `platform/engine/graph.py` construye el
`StateGraph` desde un `GraphSpec` (secuencia + bucles). La línea (2) de arriba
—registrar el destino del rechazo aunque no esté en la secuencia— sale ahora de
los propios bucles, así que vale para cualquiera.

**Los agentes son datos.** `platform/engine/agents.py` es un registro:
nombre → *entrypoint* + capacidades que compone. El motor resuelve nombres contra
él, con los perfiles `.agent.md` como reserva. Un nombre desconocido ya no falla
con un `KeyError` mudo: dice cuáles hay.

**AlejandrIA se declara como proyecto**, en
`modules/agents/domain/alejandria.py`: sus cinco agentes, lo que compone cada uno
y su bucle editorial. Es literalmente el contenido del futuro `template.yaml`.

**Las capacidades se inyectan (AC8).** El flag `AGENT_ENGINE` conmuta:

- `adapters` (por defecto) — cada agente importa su RAG y su LLM como siempre.
- `capabilities` — el motor resuelve del registro las capacidades que el agente
  declara y se las inyecta en el estado; el agente las usa vía
  `provider(state, "<nombre>", <import de siempre>)`.

Nada del camino viejo se ha borrado, que es la mitigación que pide la tabla de
riesgos de la spec.

## Decisiones documentadas

- **Las capacidades se resuelven por nombre, no por tipo.** Al conectar el
  investigador apareció que el registro de T8.2 mapeaba un tipo a **una** función,
  y el investigador no usa la misma búsqueda que el redactor: necesita
  `semantic_search_results` (con metadatos, para construir citas) y no
  `semantic_search_context` (un bloque de texto). Pedir «una capacidad de tipo
  rag» no dice cuál quieres. Se añadieron `rag_results` y `llm_stream` al registro
  y `requires` pasó a nombrar capacidades.
- **El bundle se resuelve al empezar el paso y falla ahí.** Un proyecto al que le
  falta una capacidad tiene que enterarse antes de arrancar, no a mitad del tercer
  agente y con medio artículo escrito.
- **`provider(state, nombre, fallback)` y no una inyección obligatoria.** El
  `fallback` es el import de siempre: es lo que mantiene vivos los dos caminos a
  la vez y permite compararlos. Cuando la paridad esté rodada, se retira el
  fallback y con él el import.
- **La composición se hizo donde el agente usa de verdad varias capacidades.** Los
  ocho puntos de inyección son los ocho sitios donde un adapter llamaba a
  infraestructura. No se han inventado pasos intermedios para que «parezca» más
  compuesto: la unidad de composición aquí es la capacidad, no el paso.
- **`use_cases.py` pierde los imports de los cinco agentes** y los de
  `StateGraph`/`START`/`END`. Dejarlos vivos daría a entender que el orquestador
  sigue conociéndolos, que es justo lo que esta tarea quita.
- **`route_after_revisor` y `MAX_REVIEW_LOOPS` se conservan como alias** que
  delegan en el bucle del proyecto: hay código y tests que los importan, y
  romperlos no aporta nada a AC8.

## Un cambio de conducta que conviene conocer

**Dónde se sustituye un agente en los tests ha cambiado.** Antes se parcheaba
`use_cases.run_redactor`; ahora el motor resuelve por el registro, así que hay que
parchear `adapters.redactor.run_redactor`, donde la función vive de verdad.
`tests/test_pipeline_resume.py` se actualizó por eso. Que ese fichero tuviera que
cambiar es la señal de que la indirección se movió al sitio previsto.

## Test nuevo

`backend/tests/test_engine_capability_parity.py` (24 casos):

- **Enrutado con agentes que no son los de AlejandrIA** (`recopilar`, `escribir`,
  `qa`, `publicar`): el bucle funciona, y el umbral (70) y el máximo de vueltas
  (2) son los del proyecto y no los de AlejandrIA. Es el test que el motor
  anterior no podía pasar.
- **Forma del grafo**: el destino del rechazo se registra aunque no esté en la
  secuencia; un bucle cuyo revisor no está en el flujo no arrastra nodos; una
  secuencia vacía es un error.
- **Registro de agentes**: los cinco de AlejandrIA están; un nombre desconocido
  dice cuáles hay; un agente `.agent.md` se resuelve por la reserva.
- **Capacidades**: cada agente declara las suyas y todas resuelven; una sin
  proveedor (`scrape`) y una inexistente fallan **al construir el bundle**; sin
  bundle se usa el import; con bundle, el proveedor inyectado.
- **AC5/AC8 — paridad**: el flujo completo de cinco agentes se ejecuta por los dos
  caminos con el mismo input y se comparan los estados finales.
- **Y que el flag cambia de verdad el camino**: con `adapters` ningún agente
  recibe proveedores; con `capabilities` los recibe todos. Sin este test, la
  paridad de arriba podría estar comparando el mismo camino consigo mismo.
- **El bucle sigue devolviendo al redactor**: un revisor que rechaza una vez hace
  que el redactor corra dos. Es la conducta que el `if node_name == "revisor"`
  daba por hecha.

Las dos guardias se comprobaron **por mutación**: fijando el umbral a 80 falla el
test del proyecto genérico; haciendo que `bundle_for` devuelva siempre `None`
falla el que distingue los caminos.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 619 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

npm run build && npm run build:public     # → ambos OK
python3 scripts/validate_specs.py         # → [OK]
```

## Definition of Done

- [x] **AC8** — el flag conmuta y los dos caminos dan el mismo resultado, con
  test de paridad y con la comprobación de que el flag no es decorativo.
- [x] La parte de **AC5** que toca a T8.3: el test de paridad input→output sobre
  el flujo investigador→…→publicador. **AC5 queda sin marcar** en la spec: su otra
  mitad —«proyecto creado desde el *template*»— necesita `template.yaml`, que es
  T8.4 (#210).
- [x] Tests que cubren el cambio, en verde (24 nuevos; 619 en la suite).
- [x] Builds de frontend en verde, las dos.
- [x] Docs: SPEC-013 anotada y `CLAUDE.md` con el motor y las capacidades.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **Esta tarea desbloquea T8.4 (#210)**, que sustituye
  `modules/agents/domain/alejandria.py` por `projects/alejandria-magazine/template.yaml`
  y un *loader*. El `GraphSpec`, el `ReviewLoop` y el `AgentSpec` son el esquema
  que ese YAML tiene que rellenar.
- **El flag sigue en `adapters` por defecto.** Cambiarlo a `capabilities` es una
  decisión de despliegue: la paridad está probada con agentes deterministas, no
  contra un LLM real. Recomendación: activarlo primero en un entorno de pruebas.
- **Retirar los `fallback` de `provider(...)`** es el paso que cierra la migración
  y permite borrar los imports directos. No se hace aquí a propósito: la spec pide
  explícitamente que nada se borre hasta que la paridad esté rodada.
- **`capabilities/registry.py` sigue apuntando a los adapters de AlejandrIA** para
  `format` y `publish`. Generalizarlos del todo va con T8.4, cuando exista el
  concepto de proyecto en el filesystem.
