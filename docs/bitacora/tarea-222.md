# Tarea #222 — T9.3 Harness EDD (`backend/evals/agent_behavior`)

## 2026-09-04 — Completada ✅

- **Rama:** `feat/222-edd-harness`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #222`)
- **Spec/ADR:** SPEC-014, Épica E9, ADR-0006. Criterio vinculante: **AC3**.
- **Dependencias:** ninguna declarada. Se apoya de hecho en T8.3 (registro de
  agentes del motor) y en T9.1 (traza de explicabilidad). Desbloquea T9.4 (#225)
  y T9.5 (#226).

## Qué se hizo

Un harness que ejecuta un **perfil de agente de esta plataforma** sobre un dataset
versionado y produce un informe reproducible: `backend/evals/agent_behavior/`, con
carga y validación de datasets, dos proveedores de ejecución, un registro de
métricas, el runner con CLI y el informe en dos formatos.

```bash
python -m evals.agent_behavior.runner --dataset redactor-smoke --mode replay
python -m evals.agent_behavior.runner --dataset redactor-smoke --mode live
python -m evals.agent_behavior.runner --dataset redactor-smoke --out evals/results
```

Sale con **código 1** si algún caso falla, para que T9.5 pueda usarlo tal cual sin
parsear prosa.

## La tensión del AC3, que es todo el diseño

AC3 pide un informe **reproducible** «sin depender de servicios externos no
declarados». Son dos exigencias que tiran en direcciones opuestas: medir el
comportamiento de un agente obliga a llamar a su modelo, y un modelo generativo ni
devuelve dos veces lo mismo ni está disponible en la CI. Resolverlo hacia un lado
da un harness que no se puede ejecutar; hacia el otro, uno que no mide nada.

Dos modos explícitos, y el modo es un dato de primera clase del informe:

| Modo | Qué mide | Determinista |
|---|---|---|
| `live` | El agente real, con su modelo y sus parámetros. **Mide el comportamiento.** | No |
| `replay` | Las métricas y el harness, sobre salidas grabadas. **No evalúa al modelo.** | Sí |

El fallo que había que hacer imposible es presentar un `replay` como prueba de que
el agente va bien. El modo aparece en el nombre del fichero, en el JSON y con un
aviso en la cabecera del markdown; hay un test por cada uno de los tres sitios.

## Decisiones documentadas

- **El harness no llama al LLM por su cuenta.** `PlatformProvider` ejecuta el
  agente por el mismo `resolve_runner` del motor (T8.3) y le lee tokens y fuentes
  abriendo la traza de T9.1. Una copia del prompt dentro de `evals/` mediría algo
  *parecido* al agente, y las regresiones que esto busca viven justo en esa
  diferencia: un cambio de `prompt_template` no se reflejaría.
- **Reproducible no es «byte a byte»; es «con qué se hizo».** En `live` no se puede
  prometer lo primero. El informe fija y registra modelo, proveedor, parámetros,
  `dataset_id`, versión, **hash sha256 del fichero** y commit. Sin el hash, dos
  ejecuciones del mismo `version` con contenido editado parecerían comparables: la
  versión la sube una persona y se puede olvidar, el hash no.
- **El instante va aparte del resto** (`generated_at`), porque es lo único que
  cambia entre dos ejecuciones idénticas; `report.fingerprint()` lo excluye y así
  se comparan dos informes sin él.
- **Datasets en JSONL, no YAML.** Un dataset crece por líneas: así el diff de una
  PR enseña **qué caso se añadió** en vez de un bloque reindentado.
- **Se valida al cargar, diciendo la línea.** Un caso mal formado descubierto a
  mitad de una evaluación es tiempo tirado, y en la CI un fallo así no distingue
  «el dataset está roto» de «el agente ha regresado».
- **Una métrica que no aplica se salta con motivo, no puntúa 100.** Aprobar por no
  haber mirado es mentir con buena nota, y contamina la media que T9.5 usará como
  umbral.
- **`budget` puntúa el margen, no un aprobado.** Un agente que consume el 99 % del
  presupuesto pasa igual que uno que consume el 20 %, y no son lo mismo: la
  tendencia es la señal útil.
- **Las métricas se registran, no se enumeran.** Añadir una es añadir un módulo en
  `metrics/`; el runner no se toca. Es el mismo patrón que el registro de
  capacidades de T8.3.
- **Los informes no se versionan** (`.gitignore`): son el artefacto de una
  ejecución concreta, no fuente de verdad. En CI se publicarán como artifact.

## Lo que apareció al escribir los tests

**El validador aceptaba un dataset roto.** `datos.get("input") or {}` convierte un
`[]` —tipo equivocado— en el objeto vacío, así que la comprobación de tipo nunca
llegaba a dispararse: el caso se cargaba y se evaluaba **sin su entrada**, que es
justo el fallo silencioso que este harness existe para no tener. Se comprueba el
tipo **antes** de aplicar el defecto (`_campo`), distinguiendo «ausente» de «mal
puesto»; el mismo error latente estaba en `corpus`, `expect` y `recorded_usage`.

**Y un test estaba mal, no el código.** El que vigila la frontera con
`model_benchmark` prohibía la cadena en cualquier parte del paquete, y la docstring
del `__init__.py` nombra al otro harness a propósito para decir dónde está esa
frontera. Lo que no puede pasar es que el código se **acople**: ahora se mira el
árbol de imports (AST), y se exige que la frontera siga escrita donde se lee.

## Test nuevo

`backend/tests/test_edd_harness.py` (30 casos):

- **Carga y validación**: cabecera obligatoria, ids repetidos, tipos equivocados,
  fichero vacío — cada mensaje dice el fichero y la línea. Y que editar un caso sin
  subir la versión **cambia el hash**.
- **Métricas**: una cita inventada baja la fidelidad y la nombra; no citar no es
  alucinar, salvo que el caso exija citas; el estilo y las secciones que faltan se
  enumeran; el presupuesto puntúa margen; lo que no aplica se salta con motivo.
- **Modos**: `replay` no llama al modelo, `live` construye el proveedor de la
  plataforma —no una copia—, un modo inventado se rechaza.
- **Informe**: el aviso de `replay`, el modo en el nombre del fichero, el JSON
  parseable para el gate, el contexto completo, y que **el hash llega al informe**
  (markdown y JSON).
- **Frontera** con `evals/model_benchmark/` por imports.
- **Dogfooding**: `redactor-smoke` pasa (sirve de gate) y `redactor-regressions`
  falla a propósito, un caso por regresión detectable.

Verificado **por mutación**: hacer que la fidelidad de citas nunca detecte una
inventada, que `replay` use el proveedor real, que el runner no propague el hash y
que el markdown lo oculte — cada mutación tumba su test, y volver a poner el
`or {}` del loader tumba el suyo.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 742 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

python -m evals.agent_behavior.runner --dataset redactor-smoke      --mode replay  # exit 0
python -m evals.agent_behavior.runner --dataset redactor-regressions --mode replay # exit 1 (a propósito)

npm run build && npm run build:public     # → ambos OK
python3 scripts/validate_specs.py         # → [OK]
```

`--mode live` no se ha podido ejercitar aquí: no hay Ollama ni clave de proveedor
en este entorno. Está cubierto por test en lo que se puede comprobar sin modelo
—que construye el proveedor de la plataforma y no una copia—, pero **la primera
ejecución real contra un modelo está pendiente**, y es lo primero que debería
hacer T9.4 antes de grabar conjuntos *golden*.

## Definition of Done

- [x] **AC3** — informe reproducible con modelo y parámetros fijados y
  registrados, ejecutable sin servicios externos no declarados.
- [x] Tests que cubren el cambio, en verde (30 nuevos).
- [x] Docs: SPEC-014 anotada, `README.md` del harness, `CLAUDE.md`.
- [x] Sin secretos en el diff; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **T9.4 (#225)** — conjuntos *golden* de verdad y las métricas asistidas
  (calibración del score del revisor, coherencia con juez). El juez tiene que ser
  un **modelo de la plataforma**, no un servicio externo de evaluación (SPEC-014
  §4.2); y con `temperature=0` y rúbrica fija, o el gate parpadeará.
- **T9.5 (#226)** — el gate. El JSON del informe ya trae `scores` y `passed` para
  no parsear markdown, y el código de salida ya distingue. Arrancar **en modo
  aviso** como dice §5, y calibrar umbrales sobre una línea base real: los tres
  datasets de aquí no la dan.
- **Sólo hay métricas del redactor.** El armazón es agnóstico —el caso dice a qué
  agente evalúa— pero investigador, revisor, formateador y publicador no tienen
  todavía ni caso ni métrica propia.
