# Tarea #210 — T8.4 `projects/` en filesystem: plantilla, loader y siembra

## 2026-09-03 — Completada ✅

- **Rama:** `feat/210-project-template`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #210`)
- **Spec/ADR:** SPEC-013, Épica E8, ADR-0005. Criterios: **AC4** y **AC5**.
- **Dependencias:** T8.3 (#209), ya integrada. Con ella E8 queda a falta de T8.6.

## Qué se hizo

**`backend/projects/alejandria-magazine/`** con su `template.yaml` (esquema v1) y
sus cinco `agents/*.agent.md`. La plantilla define el proyecto entero: qué agentes
tiene, qué capacidades compone cada uno, en qué orden corren y dónde vuelve el
bucle de revisión. Crear un proyecto es ahora copiar un directorio y editar un
YAML.

**`app/platform/projects/loader.py`** lo lee, **lo valida** y lo traduce a lo que
el motor entiende (`GraphSpec` + `AgentSpec`). **`profiles.py`** localiza los
`.agent.md`.

**La siembra clona lo que la plantilla declara**, en vez de barrer un directorio.

## Lo que había, y por qué importaba

**Cuatro sitios distintos buscando los perfiles a mano:**

```python
_AGENTS_DIRS = [Path("app/agents"), Path("../app/agents")]
```

en `adapters/generic.py`, `shared/agents_seed.py`, `platform/llm.py` y
`routers/agents.py`. Son rutas relativas al **directorio de trabajo**, así que el
mismo código encuentra los perfiles arrancando con `uvicorn` desde `backend/` y no
los encuentra desde la raíz del repo o con otro `WORKDIR`. Y lo peor: **no
encontrarlos no falla**. Cada sitio cae a un valor por defecto —un modelo
`llama3.2:1b`, un prompt genérico, una lista de agentes escrita a mano— así que el
síntoma aparece lejos de la causa y se parece a «el modelo se porta raro».

Ahora la raíz sale del propio paquete (`Path(__file__)`), se resuelve una vez, y
hay un test que analiza el **AST** de todo `app/` para que ningún
`Path("app/agents")` vuelva a colarse.

**La siembra barría el directorio.** `_alejandria_magazine_agents()` hacía
`glob("*.agent.md")` sobre `app/agents/`, y ahí vivían también:

- `pepe.agent.md`, cuyo propio frontmatter dice
  `prompt_template: flow-designer-persist-test`;
- `flowskill.agent.md`, un agente personalizado que alguien dejó en el repo.

Es decir: **cada proyecto nuevo nacía con dos agentes de serie que no son del
producto**, uno de ellos un resto de una prueba manual. Ahora se clona lo que la
plantilla declara. Los dos ficheros siguen en el directorio y siguen siendo
cargables como agentes dinámicos; lo que ya no son es parte del producto.

Y había un tercer efecto del `glob`: como caía a la lista escrita a mano cuando no
encontraba el directorio, esa lista llevaba tiempo divergiendo. Declaraba
`llama3.2:1b` para los cinco agentes, cuando el perfil real del investigador dice
`gemma2:2b` desde el benchmark de SPEC-025. Hay un test que fija que la siembra
toma el modelo **del perfil** y no el del fallback.

## Decisiones documentadas

- **La plantilla se valida al cargarla, no al usarla.** Una capacidad que no
  existe, una secuencia que nombra un agente no declarado, un bucle que rechaza
  hacia la nada, un perfil que falta: todo eso se rechaza con un mensaje que dice
  qué está mal. Un YAML sin validación es un YAML que falla a mitad de la tercera
  ejecución y disfrazado de otra cosa.
- **Un `profile:` no puede salirse del directorio del proyecto.** Es una ruta que
  se escribe en un fichero de configuración; sin la comprobación,
  `../../app/main.py` sería un lector de ficheros arbitrarios. Hay test.
- **`alejandria.py` no se borra: se convierte en el puente que lee la plantilla.**
  Mantiene los mismos nombres para no romper a quien ya lo usaba, y deja de
  contener la definición. Cuando haya varios proyectos, `register_project(slug)`
  lo sustituye sin más.
- **El *loader* cachea.** La plantilla se lee en cada arranque de pipeline y no
  cambia en caliente. `load.cache_clear()` la recarga (los tests lo usan).
- **Los `.agent.md` no declarados siguen indexándose.** Dejar de encontrarlos
  rompería flujos que hoy funcionan; lo que cambia es que ya no se siembran.
- **El directorio lleva guion** (`alejandria-magazine`) y no es un paquete
  importable. Es deliberado: el proyecto es **dato**, no código. El *loader* lo
  encuentra por filesystem.

## Test nuevo

`backend/tests/test_project_template.py` (27 casos):

- **AC4**: el proyecto está empaquetado; `app/agents/` ya no existe; ningún módulo
  vuelve a resolver perfiles por ruta relativa (**AST**, no `grep`: los módulos
  que arreglaron el problema lo explican en sus docstrings); la raíz de proyectos
  no depende del directorio de trabajo.
- **AC5 / paridad**: el `GraphSpec` que produce la plantilla es **exactamente** el
  que AlejandrIA tenía escrito en Python en T8.3 —secuencia, revisor, destino,
  umbral 80, 3 vueltas y destinos de reintento—, y las capacidades de los cinco
  agentes coinciden una a una. Registrar la plantilla da de alta los cinco y sus
  *entrypoints* importan de verdad.
- **Siembra**: clona los cinco declarados; toma el modelo y la temperatura **del
  perfil** y no del fallback; y ya no arrastra `pepe` ni `flowskill`.
- **Un proyecto mínimo se carga**: se escribe un `template.yaml` de un solo agente
  en un directorio temporal y se carga. Es la prueba de que «crear un proyecto es
  copiar un directorio» no es una promesa.
- **Once formas de romper una plantilla**, parametrizadas, cada una comprobando
  que el mensaje de error dice qué está mal.

Las guardias se verificaron **por mutación**: reintroducir un agente no declarado
en la siembra hace fallar dos tests; devolver un `Path("app/agents")` a
`profiles.py` hace fallar el test AST.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 646 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

npm run build && npm run build:public     # → ambos OK
python3 scripts/validate_specs.py         # → [OK]
```

## Definition of Done

- [x] **AC4** — `projects/alejandria-magazine/` con `template.yaml` y sus
  perfiles, *loader* que lo carga, y `app/agents/` sin referencias relativas.
- [x] **AC5** — el pipeline sale de la plantilla y reproduce el de AlejandrIA;
  paridad fijada en tests. Con T8.3, AC5 queda cerrado.
- [x] Tests que cubren el cambio, en verde (27 nuevos; 646 en la suite).
- [x] Builds de frontend en verde, las dos.
- [x] Docs: SPEC-013 anotada y `CLAUDE.md` con el contrato de la plantilla.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **Cambio de conducta al desplegar:** los proyectos **nuevos** dejan de nacer con
  `pepe` y `flowskill` como agentes de serie. Los proyectos existentes los
  conservan: la siembra es idempotente y no borra nada. Si se quieren quitar de
  los que ya existen, hay que hacerlo a mano.
- **El `Dockerfile` ya copia `projects/`** (`COPY . .` desde `backend/`) y
  `.dockerignore` no lo excluye. Comprobado leyendo ambos; **no se ha construido
  la imagen** porque no hay Docker en este entorno.
- **T8.6 (#212)** es lo único que queda de E8: extraer `platform/` de `projects/`
  en el frontend. Con esta tarea el backend ya tiene la separación que el front
  tiene que reflejar.
- **`capabilities/registry.py` sigue apuntando a los adapters de AlejandrIA** para
  `format` y `publish`. Ahora que existe el concepto de proyecto, moverlos a
  `projects/<slug>/capabilities/` es un paso natural — pero no era esta tarea.
