# SPEC-013: Refactor estructural e independencia de proyectos

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-06-28
- **Épica:** E8 (Plataforma no-code)
- **ADR relacionado:** ADR-0005
- **Severidad:** 🟠

## 1. Problema

`swarm-platform-builder` quiere ser una plataforma **no-code**, pero AlejandrIA
Magazine está incrustada en el núcleo y la estructura tiene inconsistencias que lo
impiden. Evidencia:

- `modules/agents/adapters/` mezcla agentes de dominio (investigador, redactor,
  revisor, formateador, publicador) con infraestructura genérica
  (`adapters/rag.py`, `adapters/scraper.py`, `adapters/tools.py`).
- El orquestador mapea *slugs* a adapters concretos y el routing está hardcodeado
  (`application/use_cases.py`: registro de nodos y `route_after_revisor`).
- Tipos de proyecto como `enum` + *seed* hardcodeado (`shared/agents_seed.py`,
  `ProjectUseCaseType`); AlejandrIA no es un *template* reutilizable.
- Duplicados *legacy*: `app/config.py` vs `app/core/config.py`; `app/database.py` vs
  `app/shared/database.py`.
- `app/models.py` monolítico (todos los modelos juntos).
- Definiciones de agentes (`.agent.md`) fuera del backend, en `app/agents/`, leídas
  por rutas relativas frágiles (`Path("app/agents")` / `"../app/agents"`).
- RAG con colección única `rag_docs` → **fuga entre proyectos** (origen del bug del
  PR #202: el documento sembrado aparecía en cualquier proyecto).

Importa porque sin esta base no se puede ofrecer no-code real ni aislar proyectos,
y cada proyecto nuevo seguiría exigiendo código.

## 2. Objetivos / No-objetivos

- **Objetivos:**
  - Separar el **motor** (`platform/`, genérico) de los **paquetes de proyecto**
    (`projects/<slug>/` en filesystem), según ADR-0005.
  - Empaquetar AlejandrIA como `projects/alejandria-magazine/` (template + agentes),
    de modo que el *seed* clone desde el paquete en vez de código hardcodeado.
  - Lograr **independencia de proyectos** en datos, RAG, runtime y capacidades.
  - Eliminar duplicados de `config`/`database`, partir `models.py` por módulo y
    unificar el HTTP en un único sitio.
  - **Paridad de comportamiento**: AlejandrIA funciona igual antes y después.
- **No-objetivos:**
  - El editor no-code completo en el front (SPEC-011), el grafo/routing data-driven
    avanzado (SPEC-009), los canales de publicación nuevos (SPEC-012) y el registro
    de capacidades como producto (SPEC-008). Esta spec entrega la **base estructural**
    y la **independencia**; esas specs construyen encima.
  - Cambiar el motor LLM (sigue Ollama).

## 3. Criterios de aceptación (Given/When/Then)

- [x] **AC1** — *Given* el backend, *When* se inspeccionan config y base de datos,
  *Then* existe un único módulo de configuración y uno de base de datos bajo `core/`
  (no quedan `app/config.py` ni `app/database.py` duplicados) y la app arranca.
- [x] **AC2** — *Given* el backend, *When* se inspeccionan los modelos, *Then*
  `app/models.py` monolítico ya no existe: cada modelo vive en su módulo y los tests
  existentes siguen pasando.
- [x] **AC3** — *Given* el motor, *When* se listan las capacidades, *Then* existe un
  `platform/capabilities/registry.py` con capacidades tipadas (rag/search/scrape/
  format/publish/llm) y la infraestructura (`rag`, `scraper`, `tools`, `llm`) vive
  bajo `platform/`, no bajo `modules/agents/adapters/`.
- [x] **AC4** — *Given* la estructura de proyectos, *When* se arranca en limpio,
  *Then* existe `projects/alejandria-magazine/` con `template.yaml` y `agents/*.agent.md`,
  y un *loader* lo carga; `app/agents/` ya no se referencia por ruta relativa.
  <br>*T8.4 (#210)*: `backend/projects/alejandria-magazine/` con su
  `template.yaml` (esquema v1) y los cinco perfiles.
  `platform/projects/loader.py` lo lee, **lo valida** y lo traduce a `GraphSpec` +
  `AgentSpec`. `app/agents/` ya no existe: las cuatro rutas relativas que lo
  buscaban —runner genérico, siembra, resolutor de modelos y router— se
  sustituyeron por una resolución basada en el paquete, y hay un test AST que
  impide que vuelvan.
- [x] **AC5** — *Given* un proyecto nuevo creado desde el *template* AlejandrIA,
  *When* se ejecuta su pipeline, *Then* produce el mismo resultado que el AlejandrIA
  actual (test de **paridad** input→output sobre el flujo investigador→…→publicador).
  <br>*T8.3 (#209)*: el test de paridad sobre el flujo completo, comparando los
  dos caminos del motor.
  <br>*T8.4 (#210)*: el pipeline sale ya de la plantilla. La paridad se fija
  comparando el `GraphSpec` y las capacidades que produce `template.yaml` con los
  que AlejandrIA tenía escritos en Python, y comprobando que la siembra clona lo
  que la plantilla declara con el modelo y la temperatura del perfil (no los del
  fallback).
- [x] **AC6** — *Given* dos proyectos con documentos RAG distintos, *When* uno ejecuta
  su pipeline, *Then* solo recupera documentos de **su** proyecto (RAG con *namespace*
  por proyecto); ningún documento de otro proyecto ni del *seed* de demo se filtra.
  <br>*T8.5 (#211)*: el nombre de la colección **se deriva, no se recibe** —
  `platform/project_context.py` compone `p_<project_id>__<bucket>` y es el único
  sitio que lo hace. Se cerraron tres puertas: la colección salía del perfil del
  agente (dos proyectos con la misma plantilla compartían `rag_docs`);
  `rag_collection` es un campo que escribe la persona usuaria, así que bastaba
  teclear el de otro; y la consulta de perfiles de la ejecución no filtraba por
  proyecto, con lo que el pipeline podía arrancar con el modelo, el prompt y los
  `rag_doc_ids` del vecino. El *seed* de demo va ahora al espacio del proyecto del
  sistema. `scripts/migrate_rag_namespaces.py` mueve lo heredado.
- [x] **AC7** — *Given* el front, *When* se inspecciona `frontend/src`, *Then* el
  *builder* reutilizable vive en `platform/` separado de las vistas de consumo en
  `projects/`, y `npm run build` y `npm run build:public` siguen compilando.
  <br>*T8.6 (#212)*: `src/platform/` (api, stores, componentes y páginas de
  construcción) y `src/projects/alejandria-magazine/` (artículos, revista, paper
  y su catálogo de agentes). La dependencia va **en un solo sentido** y hay un
  test que lo comprueba. El catálogo de los cinco agentes estaba escrito
  **cuatro veces**, una de ellas dentro de un componente del builder: ahora el
  proyecto se registra al arrancar (`setAgentCatalog`, `setProjectNavItems`,
  `setRunTarget`, `setNotificationRoute`) y el builder pregunta.
- [x] **AC8** — *Given* la migración, *When* se conmuta el *feature flag*
  adapter↔capacidades, *Then* ambos caminos producen el mismo resultado hasta retirar
  los adapters legacy.
  <br>*T8.3 (#209)*: el flag es `AGENT_ENGINE` (`adapters` por defecto |
  `capabilities`). Cada agente declara en `alejandria.py` **qué capacidades
  compone**; en modo `capabilities` el motor las resuelve del registro y se las
  inyecta, y en modo `adapters` el agente usa sus imports de siempre. Nada del
  camino viejo se ha borrado. Hay un test de paridad sobre el flujo completo y
  otro que comprueba que el flag **cambia de verdad el camino**, para que la
  paridad no acabe comparando el mismo camino consigo mismo.

## 4. Diseño propuesto

Sigue ADR-0005. Resumen por área:

- **`core/`** *(hecho — T8.1, #237)*: fusionar `app/config.py` → `app/core/config.py`;
  `app/database.py` → `app/core/database.py`. Imports actualizados.
- **`platform/`**: nuevo paquete motor.
  - `engine/graph.py` + `engine/routing.py` + `engine/agents.py` (desde
    `application/use_cases.py`, con routing como datos) *(hecho — T8.3, #209)*:
    el motor ya no menciona a `revisor` ni a `redactor`; la forma del pipeline
    sale de un `GraphSpec` y los nodos del registro de agentes.
  - `capabilities/registry.py` + subcarpetas *(hecho — T8.2, #239)*: movidos
    `rag.py`, `tools.py` y `shared/llm.py` → `platform/`. (`scraper.py` ya no
    existe: eliminado como código muerto, SPEC-002 Superseded; la capacidad
    `scrape` queda declarada sin proveedor en el registry.)
  - `agents/generic_runner.py` (desde `generic.py`) — pendiente (T8.3).
- **`modules/`**: hexagonal consistente (`domain/application/infrastructure/interface`);
  partir `models.py` *(hecho — T8.1)*; nuevo módulo `templates/`.
- **`projects/<slug>/`** (filesystem) *(hecho — T8.4, #210)*: `template.yaml`
  (agentes, grafo y bucles de revisión), `agents/*.agent.md`. *Loader* que valida
  y registra el paquete, y *seed* que clona a BD lo que la plantilla declara.
- **Independencia**: `ProjectContext` en el runtime; repos con *project scoping*;
  colección/namespace RAG por proyecto (`rag_<project_id>` o filtro `project_id`).
- **Frontend** *(hecho — T8.6, #212)*: `platform/` (builder) separado de
  `projects/<slug>/` (consumer), con el proyecto registrándose en el builder al
  arrancar en vez de que el builder lo importe.

Contratos: el `template.yaml` define el esquema de un proyecto (versión `v1`). Las
capacidades exponen un *schema* de entradas/salidas estable que el grafo conecta.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Romper AlejandrIA al generalizar adapters | Alto | Tests de **paridad** por adapter antes de sustituir; *feature flag* adapter↔capacidades; nada se borra hasta pasar paridad (AC5, AC8). |
| Migración RAG entre colecciones | Medio | Script de migración idempotente + *rollback*; *namespace* nuevo conviviendo con el viejo durante la transición (AC6). |
| Refactor transversal de imports | Medio | Pasos pequeños y PRs independientes; CI verde en cada paso. |
| Rutas de `.agent.md` rotas al mover | Bajo | *Loader* centralizado con ruta basada en el paquete; sin rutas relativas dispersas (AC4). |

## 6. Plan de pruebas

- **Unitarias:** registro de capacidades (schema/contratos); *loader* de paquetes;
  `ProjectContext`; *project scoping* en repos.
- **Integración / paridad:** ejecutar el flujo AlejandrIA actual y el reconstruido
  desde `template.yaml` con el mismo input y comparar salida (AC5, AC8).
- **Aislamiento:** dos proyectos con RAG distinto; verificar que no hay fuga (AC6) —
  reutiliza el escenario del bug del PR #202.
- **Build:** `python -m pytest -q` backend; `npm run build` y `npm run build:public`
  frontend (AC7).

## 7. Impacto operativo / observabilidad

- **Migraciones:** nuevo *namespace* RAG por proyecto; tablas de `templates` (si
  aplica). *Rollout* por pasos detrás de *feature flag*; *rollback* = desactivar flag
  y conservar adapters legacy hasta su retirada.
- **Logs:** el runtime registra `project_id` y la capacidad ejecutada en cada *step*
  para trazabilidad por proyecto.
- **Sin cambios de API pública** en los primeros pasos (chore estructural); los
  contratos del `template.yaml` y capacidades se versionan (`v1`).

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E8
  title: Plataforma no-code (motor + independencia de proyectos)
  area: area/backend
tasks:
  - id: T8.1
    title: "Consolidar config/database duplicados, partir models.py y unificar HTTP"
    sev: medium
    depends_on: []
    acceptance: [AC1, AC2]
  - id: T8.2
    title: "Crear platform/capabilities + registry; mover rag/scraper/tools/llm al motor"
    sev: high
    depends_on: [T8.1]
    acceptance: [AC3]
  - id: T8.3
    title: "Reescribir adapters de AlejandrIA como composicion de capacidades con tests de paridad"
    sev: high
    depends_on: [T8.2]
    acceptance: [AC5, AC8]
  - id: T8.4
    title: "projects/ en filesystem: empaquetar AlejandrIA (template.yaml + agents) y loader; seed clona"
    sev: high
    depends_on: [T8.3]
    acceptance: [AC4, AC5]
  - id: T8.5
    title: "Independencia de proyectos: ProjectContext, project scoping y RAG namespace por proyecto"
    sev: high
    depends_on: [T8.1]
    acceptance: [AC6]
  - id: T8.6
    title: "Frontend: extraer platform/ (builder) de projects/ (consumer)"
    sev: medium
    depends_on: [T8.4]
    acceptance: [AC7]
```
