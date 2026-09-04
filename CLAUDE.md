# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es esto

Plataforma de orquestación de agentes IA (FastAPI + LangGraph + Qdrant). El
proyecto de referencia es **AlejandrIA Magazine**: un pipeline de 5 agentes
(investigador → redactor → revisor → formateador → publicador) para producir
artículos científicos. El README documenta exhaustivamente el producto, la API y
el pipeline editorial; **no lo repitas aquí** — consúltalo cuando trabajes en esa
funcionalidad.

Dos sentidos de "agente" conviven en el repo, no los confundas:
- **Agentes de producto**: perfiles en BD + `backend/app/agents/*.agent.md`,
  ejecutados por el orquestador LangGraph. Son la funcionalidad.
- **Agentes de desarrollo**: `.claude/agents/` (`task-runner`, `sdd-sync`), que
  implementan el backlog. Son tooling de este repo.

## Comandos

Backend (Python 3.12, dir `backend/`):
```bash
# Tests — requieren estas env vars o la validación de config aborta el import:
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q   # desde backend/
python -m pytest tests/test_auth_rate_limit_lockout.py -v          # un archivo
python -m pytest -k lockout -v                                      # por nombre
uvicorn app.main:app --reload --port 8000                           # servidor dev

# Esquema — Alembic (SPEC-018/T4.1). init_db ya aplica `upgrade head` al arrancar;
# estos comandos son para trabajar el esquema a mano:
alembic current                            # revisión aplicada
alembic check                              # ¿los modelos van por delante?
alembic revision --autogenerate -m "..."   # nueva migración desde los modelos
alembic upgrade head / downgrade -1

# Dependencias — lock con hashes (SPEC-020/T6.3). NO edites requirements.txt:
# los rangos van en requirements.in y el lock se recompila desde ahí, con 3.12.
pip install --require-hashes -r requirements.txt          # instalar como la CI
pip-compile --generate-hashes --no-strip-extras \
    --output-file requirements.txt requirements.in        # tras tocar requirements.in
```
No hay `pytest.ini`/`pyproject.toml`: los tests se invocan con `python -m pytest`
desde `backend/` y fijan su propio `DATABASE_URL` (SQLite) en tiempo de import.

**Nunca cambies el esquema con SQL a mano.** `app/core/database.py` tenía 15
`ALTER TABLE` dentro de un `try/except: pass` que se tragaba los fallos; ya no.
Todo cambio de modelo va por una migración en `backend/alembic/versions/`, y
`tests/test_migrations.py` compara el esquema migrado con `create_all` para que no
divergan. Revisa siempre lo que genera `--autogenerate`: hay un ciclo de FKs
`users` ↔ `projects` que no sabe ordenar. Ver `backend/alembic/README`.

Frontend (dir `frontend/`):
```bash
npm install
npm run dev            # Vite :5173
npm run build          # build app principal — DEBE pasar antes de PR
npm run build:public   # build de la revista pública (vite.public.config.js)
```
Hay **dos** builds Vite: la app principal (`index.html`) y la revista pública
(`index.public.html` / `vite.public.config.js`). Si tocas el frontend público,
verifica ambos.

**Dos capas en `frontend/src/` (T8.6)**, con la misma separación que el backend:
- `platform/` — el *builder* reutilizable: cliente HTTP, stores de sesión y
  proyectos, componentes, Flow Designer, agentes, documentos, usuarios.
- `projects/<slug>/` — las vistas de consumo: en AlejandrIA, artículos, revista y
  maquetación de paper, más su `catalog.jsx`.

**La dependencia va en un solo sentido**: `platform/` **no** importa de
`projects/`, y hay un test que lo comprueba (`test_frontend_layers.py`). Lo que el
builder necesita saber del proyecto se registra al arrancar en `main.jsx`
(`setAgentCatalog`, `setProjectNavItems`, `setRunTarget`, `setNotificationRoute`)
y el builder pregunta a esos registros. Si el lienzo necesita un dato nuevo del
proyecto, se añade un registro; no se importa.

Arranque local completo (Windows): `dev-local.cmd` levanta Qdrant + backend
(`:8000`, SQLite) + frontend (`:5173`) en ventanas separadas. No confundir con
Docker (`docker compose up --build`, backend en `:8080`).

## Arquitectura (lo que no se ve en un solo archivo)

- **El backend real vive en `backend/app/`** (el `app/` de la raíz está vacío,
  ignóralo). `backend/app/models.py` mezcla ORM SQLAlchemy y DTOs Pydantic en un
  único archivo.
- **Orquestador**: `backend/app/modules/agents/application/use_cases.py` ejecuta el
  grafo y pasa un `AgentState` (TypedDict) tipado entre nodos. **La forma del
  pipeline es un dato** (T8.3): `backend/app/platform/engine/` construye el
  `StateGraph` desde un `GraphSpec` —secuencia + bucles de revisión— y resuelve
  cada nodo contra un registro de agentes. El motor no menciona a ningún agente
  concreto; AlejandrIA se declara en
  `backend/app/modules/agents/domain/alejandria.py` (sus cinco agentes, las
  capacidades que compone cada uno y el bucle revisor→redactor), que es lo que
  T8.4 moverá a `template.yaml`. Si añades un agente, regístralo ahí; si cambias
  el bucle, es un campo de `ReviewLoop`, no un `if`.
  Cada ejecución se registra en la tabla `agent_runs`. El bucle Revisor→Redactor
  (`loop_count`, máx 3) y el **HITL** (`await_decision`, pausa por SSE) viven aquí.
- **Streaming**: el pipeline emite eventos por **SSE** (`/agents/{id}/stream`):
  `agent_start`, `token`, `await_decision`, `done`, `cancelled`, … La cancelación
  y la decisión humana son endpoints aparte que actúan sobre la ejecución en curso.
- **LLM**: `backend/app/platform/llm.py` es el dispatcher único
  Anthropic/Ollama/OpenAI (`LLM_PROVIDER`). Cada agente usa `keep_alive=0` para
  liberar VRAM al terminar y un `num_ctx` fijo — relevante si tocas
  tiempos/memoria del pipeline.
- **Capacidades (T8.3)**: `backend/app/platform/capabilities/registry.py` declara
  las capacidades del motor (`rag`, `rag_results`, `llm`, `llm_stream`, `search`,
  `format`, `publish`) y `binding.py` las resuelve para un agente. Con
  `AGENT_ENGINE=capabilities` el motor inyecta a cada agente las que declara y el
  agente las usa vía `provider(state, "<nombre>", <import de siempre>)`; con
  `AGENT_ENGINE=adapters` (por defecto) no se inyecta nada y cada agente usa su
  import. Los dos caminos deben dar el mismo resultado — hay un test de paridad.
- **RAG**: `backend/app/platform/capabilities/rag.py` (extracción PDF, chunking,
  embeddings `nomic-embed-text` 768-dim, Qdrant). Busca en el bucket del agente +
  la biblioteca `__library__`. No hay scraping web.
- **Aislamiento por proyecto (T8.5)**: el nombre de la colección de Qdrant **se
  deriva, no se recibe**. `backend/app/platform/project_context.py` es el único
  sitio que lo compone: `p_<project_id>__<bucket>`, donde el *bucket* es lo que
  aporta el perfil del agente (`rag_collection`, un campo que escribe la persona
  usuaria). Así `__library__` es compartida **dentro** del proyecto y un perfil no
  puede apuntar al espacio de otro. Las peticiones llevan el proyecto en la
  cabecera `X-Project-Id`, que resuelve y autoriza `project_access.py`; en el
  pipeline viaja en `AgentState.project_id`. Si tocas una ruta que lee o escribe
  documentos, pídele la dependencia `get_project_context` — hay un test que lo
  comprueba. Para bases anteriores:
  `python scripts/migrate_rag_namespaces.py --apply`.
- **Config con precedencia**: env vars > `config.yaml` (raíz o `backend/`) >
  defaults en `backend/app/core/config.py`. En producción `SECRET_KEY` es
  obligatorio; en debug se autocrean usuarios y admin.

## Flujo de trabajo obligatorio (SDD + gobernanza)

Este repo se rige por **Spec-Driven Development** y una gobernanza estricta. Antes
de cambiar código lee [GOVERNANCE.md](docs/governance/GOVERNANCE.md). Lo esencial:

- **Contrato de nombres de rama** (GOVERNANCE §3): toda rama lleva prefijo
  obligatorio — `feat/` (funcionalidad), `fix/` (bug), `docs/` (documentación),
  `chore/` (mantenimiento sin impacto funcional), `sec/` (seguridad). **Nunca**
  ramas sin prefijo ni trabajo sobre `develop`.
- **Entrega siempre por PR contra `develop`** con `Closes #N`. **Ningún agente
  mergea su propia PR ni cierra issues a mano** (§3.1).
- **Fuente de verdad de la definición**: `docs/specs/` + `docs/adr/`. El **estado
  de ejecución** (open/closed) vive en el GitHub Project. `/sdd-sync` reconcilia
  una con otra **sin tocar el estado** (dry-run por defecto; `--apply` para aplicar).
- **Resolver una tarea**: `/resolve-task <#>` (o `bash scripts/run-task.sh <#>`)
  implementa una tarea de extremo a extremo y deja una **bitácora** datada en
  `docs/bitacora/tarea-<N>.md` por ejecución exitosa.
- **Definition of Done** (§6): criterios de aceptación cumplidos, tests que cubren
  el cambio en verde, docs/spec/ADR actualizados, sin secretos en el diff.
- **Datos y retención**: [docs/governance/data-retention.md](docs/governance/data-retention.md)
  fija qué se guarda y cuánto. Si tocas una ventana `RETENTION_*` o añades una tabla
  que acumule rastro, actualiza ese documento — hay un test que lo comprueba.
- **Autoría de specs (Spec Kit, ADR-0007)**: las specs nacen con
  `/speckit-specify` (Draft desde TEMPLATE) y maduran con `/speckit-clarify`,
  `/speckit-checklist` y `/speckit-analyze` antes de pasar a Ready — paso
  **recomendado de la DoR (§5), no bloqueante en CI** (el gate duro sigue siendo
  `scripts/validate_specs.py`). Toda épica del Project debe estar respaldada por
  una spec con bloque `sdd-sync` (E1–E6 se adoptaron en SPEC-015…020). Ver
  [docs/governance/speckit-authoring-aids.md](docs/governance/speckit-authoring-aids.md).

### Guardarraíles activos (hooks)

`.claude/hooks/` (`PreToolUse`) **bloquean** antes de actuar: commit/push directo a
ramas protegidas, force-push, `--no-verify`, `git add -f` de secretos y `rm -rf`
catastrófico. Si un commit a `develop` falla con un mensaje de gobernanza, es el
hook: crea una rama con prefijo y abre PR.

### CI (gate de PR a develop)

`.github/workflows/ci.yml` corre en cada PR: `pytest` backend, `npm run build`
frontend, validación de specs (`scripts/validate_specs.py`), auditoría de
dependencias (`pip-audit` + `npm audit`, job `deps-audit`) y escaneo de secretos
(gitleaks). Dependabot (`.github/dependabot.yml`) actualiza backend, frontend y
Actions cada semana. Hay además review automática de Claude y un digest diario
(`.github/workflows/claude-*.yml`).

## graphify (grafo de conocimiento — tooling local)

Herramienta de desarrollo, no funcionalidad del producto. Construye un grafo de
conocimiento navegable del backend (god nodes, comunidades, relaciones entre
archivos) en `backend/graphify-out/` — **ignorado por git** (`.gitignore`), es un
artefacto local por máquina. Skill de Claude Code: `/graphify`. Dep de dev en
`requirements-dev.txt` (`graphifyy`); los hooks del guardián viven en
`.claude/settings.local.json` (local, no versionado).

Cómo usarlo al responder sobre el código:
- Si existe `backend/graphify-out/graph.json`, para preguntas sobre el código usa
  el grafo antes que grep crudo:
  `graphify path "<A>" "<B>" --graph backend/graphify-out/graph.json` para
  relaciones y `graphify explain "<concepto>" --graph backend/graphify-out/graph.json`
  para un nodo concreto. Devuelven un subgrafo acotado, mucho menor que el reporte
  o un grep completo.
- `backend/graphify-out/GRAPH_REPORT.md` solo para revisión amplia de arquitectura
  cuando path/explain no dan contexto suficiente.
- Tras modificar código, `graphify update backend` mantiene el grafo al día (solo
  AST, sin coste de API). El hook post-commit local ya lo reconstruye tras commit.
