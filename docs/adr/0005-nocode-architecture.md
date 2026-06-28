# ADR-0005: Arquitectura no-code — motor vs paquetes de proyecto e independencia de proyectos

- **Estado:** Propuesto
- **Fecha:** 2026-06-28
- **Decisores:** Equipo de plataforma
- **Specs relacionadas:** SPEC-013 (refactor estructural e independencia de proyectos); habilita SPEC-008…012 (épica E8)

## Contexto

El producto global es **swarm-platform-builder**: una plataforma que debería permitir
al usuario construir su propia lógica de agentes **sin escribir código** desde el
front. Hoy solo es **medio no-code**:

- Los agentes "custom" ya se ejecutan desde configuración mediante el runner
  genérico (`backend/app/modules/agents/adapters/generic.py`): modelo, temperatura,
  `prompt_template` con variables, RAG y tools.
- Pero el proyecto **AlejandrIA Magazine** está **incrustado en el núcleo**:
  - Sus 5 agentes (investigador, redactor, revisor, formateador, publicador) son
    *adapters* Python a medida con lógica específica (EuropePMC, scraping, formato
    científico, maquetación, publicación).
  - El orquestador mapea esos 5 *slugs* a esos adapters concretos
    (`application/use_cases.py`), con un *fallback* genérico para el resto.
  - El enrutamiento condicional (bucle revisor→redactor por *score*, `add_source`)
    está hardcodeado (`route_after_revisor`).
  - Los **tipos de proyecto** son un `enum` (`ProjectUseCaseType`) con funciones de
    *seed* hardcodeadas (`shared/agents_seed.py`); AlejandrIA no es un *template*
    reutilizable, es código.

Además, la estructura tiene inconsistencias que dificultan el objetivo:

- `modules/agents/adapters/` mezcla **implementaciones de agentes de dominio** con
  **infraestructura** genérica (`rag.py`, `scraper.py`, `tools.py`).
- Duplicados *legacy*: `app/config.py` vs `app/core/config.py`; `app/database.py` vs
  `app/shared/database.py`.
- `models.py` es monolítico (todos los modelos juntos, no por módulo).
- HTTP en dos sitios: `routers/` plano y `modules/*/adapters/http.py`.
- Las definiciones de agentes (`.agent.md`) viven **fuera** del backend (`app/agents/`)
  y se leen por rutas relativas frágiles.
- **Independencia de proyectos incompleta**: los datos llevan `project_id`, pero el
  RAG comparte una sola colección (`rag_docs`) → fuga entre proyectos (origen del
  bug corregido en PR #202, donde el documento sembrado "bienvenida" aparecía en
  artículos de cualquier proyecto).

Fuerzas: queremos (1) que el usuario componga lógica sin código; (2) que AlejandrIA
sea *un proyecto más*, preconfigurado como plantilla; (3) que un developer extienda
**capacidades** (no tipos de proyecto) en código; (4) aislamiento real entre
proyectos; (5) no romper AlejandrIA durante la transición.

## Decisión

Adoptaremos una arquitectura que **separa el motor (código genérico, no-code) de los
paquetes de proyecto (contenido)** y trata cada proyecto como una unidad
**independiente y autocontenida**.

### 1. Frontera motor / proyecto

| Capa | Quién la toca | Qué es |
|------|---------------|--------|
| **Capacidades / tools / integraciones** | Developer (código) | *Plugins* registrados: `rag_search`, `external_search`, `web_scrape`, `format`, `publish`, `llm`… con *schema* tipado de entradas/salidas. |
| **Templates de proyecto** | Datos (clonables) | Un proyecto = agentes + grafo + routing + RAG + canales de salida. AlejandrIA = un *template*. |
| **Agentes y flujos** | Usuario (no-code, front) | Compone agentes (prompt + modelo + capacidades + RAG) y los conecta en un grafo con reglas. |

El developer diferencia proyectos por su **paquete/manifiesto**, **no** por un `enum`.

### 2. Los proyectos son **paquetes en el filesystem**

Cada proyecto vive en `projects/<slug>/` como paquete versionable y autocontenido:

```
projects/
  alejandria-magazine/
    template.yaml        # agentes + grafo + routing + rag + canales de salida
    agents/*.agent.md    # definiciones (se mueven aquí desde app/agents)
    capabilities/        # (opcional) capacidades propias del proyecto
    assets/
```

Crear un proyecto = elegir un *template* (paquete) y clonarlo a la BD. AlejandrIA se
empaqueta como `projects/alejandria-magazine/` y el *seed* deja de ser código
hardcodeado: clona desde el paquete. Los *templates* creados por el usuario en el
front se guardan en BD; los *templates* base se distribuyen como paquetes en el repo.

### 3. Estructura objetivo del backend

```
backend/app/
  core/                      # config + security + db en UN solo sitio (elimina duplicados)
  platform/                  # EL MOTOR no-code, agnóstico de proyecto
    engine/
      graph.py               # compila/ejecuta el grafo (ex use_cases.py)
      runtime.py             # runtime de "steps" + ProjectContext
      routing.py             # aristas condicionales data-driven (ex route_after_revisor)
    capabilities/            # registro de capacidades = código del developer
      registry.py
      rag/ search/ scrape/ format/ publish/ llm/
    agents/
      generic_runner.py      # ejecución de agente desde config (ex generic.py)
  modules/                   # contextos de negocio, hexagonal consistente
    projects/   {domain, application, infrastructure, interface}
    templates/  {…}          # plantillas de proyecto como datos
    articles/   {…}
    auth/       {…}
    flows/      {…}
  interface/http/            # ensamblado de routers (un único sitio)
  shared/
```

### 4. Independencia de proyectos en cuatro planos

| Plano | Hoy | Objetivo |
|-------|-----|----------|
| **Datos** | `project_id` en tablas | Repositorios con *project scoping* obligatorio: toda consulta filtra por proyecto. |
| **RAG / vectores** | colección única `rag_docs` (fuga) | *Namespace* por proyecto: `rag_<project_id>` o filtro `project_id` en el *payload*. |
| **Runtime** | estado global + adapters fijos | El motor recibe un **`ProjectContext`** (template, capacidades habilitadas, colección RAG, canales) y nada fuera de él. |
| **Capacidades** | embebidas en AlejandrIA | Registro global en código; cada proyecto **declara** en su `template.yaml` cuáles usa. |

Resultado: un proyecto es **exportable/importable** y dos proyectos nunca se
contaminan.

### 5. Frontend

Separar el *builder* (no-code, reutilizable) del *consumer* (la revista):

```
frontend/src/
  app/        # bootstrap + router
  platform/   # builder: flow editor, agent editor, capability picker, template manager
  projects/   # vistas de consumo (magazine, reader)
  shared/     # ui (ds), api client, stores
```

(El *build* público ya se separó en PR #200; esto lo formaliza.)

### 6. Plan de migración (incremental, sin romper AlejandrIA)

De menor a mayor riesgo, cada paso es un PR independiente (detalle y criterios en
SPEC-013):

1. **chore estructural**: consolidar `config`/`database` duplicados; partir
   `models.py` por módulo; unificar HTTP en un sitio.
2. **`platform/capabilities` + registry**: mover `rag/scraper/tools/llm` al motor.
3. **Reescribir los adapters de AlejandrIA como composición de capacidades**, con
   **tests de paridad** (mismo input → mismo output) y *feature flag* adapter↔steps.
4. **`projects/` en filesystem**: extraer AlejandrIA a `projects/alejandria-magazine/`
   (mover `.agent.md`, crear `template.yaml`); *loader* de paquetes; el *seed* clona.
5. **RAG por proyecto** (*namespace*) → cierra la independencia y elimina la fuga.
6. **Frontend**: extraer `platform/` (builder) de `projects/`.

## Alternativas consideradas

- **Templates puramente en BD (sin paquetes en filesystem).** Pros: un solo lugar
  para todo; edición 100% por UI. Contras: los *templates* base no se versionan con
  el código, peor *diffing*/revisión y reproducibilidad en *clones*; difícil
  distribuir capacidades de proyecto. **Descartada** para los *templates base*
  (los *templates de usuario* sí van a BD).
- **Mantener adapters por proyecto (status quo, más adapters).** Pros: mínimo
  esfuerzo. Contras: no es no-code; cada proyecto nuevo exige código; no escala.
- **Motor de workflow externo (p. ej. orquestador de terceros).** Pros: potencia.
  Contras: gran acoplamiento e *infra*; *overkill* para el modelo de agentes actual
  y contrario a la simplicidad del despliegue.

## Consecuencias

- **Positivas:**
  - El usuario crea lógica sin tocar código; AlejandrIA queda como *template* base.
  - Aislamiento real entre proyectos (datos + RAG + runtime).
  - El developer extiende **capacidades** (plugins) en vez de tipos de proyecto.
  - Estructura coherente; se eliminan duplicados y ambigüedades de carpetas.
- **Negativas / coste:**
  - Refactor transversal con riesgo de regresión en AlejandrIA → mitigado con tests
    de paridad y *feature flags*; nada se borra hasta que su reemplazo pasa paridad.
  - Migración de datos (RAG *namespace*, *templates*) requiere cuidado y *rollback*.
- **Seguimiento:**
  - SPEC-013 detalla el refactor estructural y la independencia (épica E8).
  - SPEC-008…012 (a materializar) cubren capacidades, grafo data-driven, templates,
    editor no-code y canales de publicación sobre esta base.
