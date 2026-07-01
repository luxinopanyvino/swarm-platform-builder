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
pip install -r requirements.txt
```
No hay `pytest.ini`/`pyproject.toml`: los tests se invocan con `python -m pytest`
desde `backend/` y fijan su propio `DATABASE_URL` (SQLite) en tiempo de import.

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

Arranque local completo (Windows): `dev-local.cmd` levanta Qdrant + backend
(`:8000`, SQLite) + frontend (`:5173`) en ventanas separadas. No confundir con
Docker (`docker compose up --build`, backend en `:8080`).

## Arquitectura (lo que no se ve en un solo archivo)

- **El backend real vive en `backend/app/`** (el `app/` de la raíz está vacío,
  ignóralo). `backend/app/models.py` mezcla ORM SQLAlchemy y DTOs Pydantic en un
  único archivo.
- **Orquestador**: `backend/app/modules/agents/application/use_cases.py` construye
  un LangGraph `StateGraph` y pasa un `AgentState` (TypedDict) tipado entre nodos.
  Cada ejecución se registra en la tabla `agent_runs`. El bucle Revisor→Redactor
  (`loop_count`, máx 3) y el **HITL** (`await_decision`, pausa por SSE) viven aquí.
- **Streaming**: el pipeline emite eventos por **SSE** (`/agents/{id}/stream`):
  `agent_start`, `token`, `await_decision`, `done`, `cancelled`, … La cancelación
  y la decisión humana son endpoints aparte que actúan sobre la ejecución en curso.
- **LLM**: `backend/app/shared/llm.py` es el dispatcher único Ollama/OpenAI
  (`LLM_PROVIDER`). Cada agente usa `keep_alive=0` para liberar VRAM al terminar y
  un `num_ctx` fijo — relevante si tocas tiempos/memoria del pipeline.
- **RAG**: `backend/app/modules/agents/adapters/rag.py` (extracción PDF, chunking,
  embeddings `nomic-embed-text` 768-dim, Qdrant). Busca en el bucket del agente +
  la biblioteca compartida `__library__`. No hay scraping web.
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
- **Ayudas de autoría (opcionales)**: `/speckit-clarify`, `/speckit-checklist` y
  `/speckit-analyze` (adaptadas de [spec-kit](https://github.com/github/spec-kit))
  ayudan a pulir un SPEC antes de pasarlo a Ready. Son **complemento**, no parte
  del flujo ni de la DoD. Ver
  [docs/governance/speckit-authoring-aids.md](docs/governance/speckit-authoring-aids.md).

### Guardarraíles activos (hooks)

`.claude/hooks/` (`PreToolUse`) **bloquean** antes de actuar: commit/push directo a
ramas protegidas, force-push, `--no-verify`, `git add -f` de secretos y `rm -rf`
catastrófico. Si un commit a `develop` falla con un mensaje de gobernanza, es el
hook: crea una rama con prefijo y abre PR.

### CI (gate de PR a develop)

`.github/workflows/ci.yml` corre en cada PR: `pytest` backend, `npm run build`
frontend, validación de specs (`scripts/validate_specs.py`) y escaneo de secretos
(gitleaks). Hay además review automática de Claude y un digest diario
(`.github/workflows/claude-*.yml`).
