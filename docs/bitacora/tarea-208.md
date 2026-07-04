# Tarea #208 — T8.2 Crear platform/capabilities + registry; mover rag/scraper/tools/llm al motor

## 2026-07-04 12:27 — Completada ✅

- **Rama:** `feat/208-platform-capabilities-registry`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #208`)
- **Spec/ADR:** SPEC-013 (Refactor estructural e independencia de proyectos),
  Épica E8, ADR-0005. Criterio vinculante de T8.2: **AC3**.
- **Dependencias:** #207 (T8.1) — **cerrada y mergeada** (PR #237).

### Qué se hizo
Se creó el paquete motor `backend/app/platform/` y se movió la infraestructura
genérica fuera de `modules/agents/adapters/`, con `git mv` para preservar la
historia:

- `modules/agents/adapters/rag.py` → `platform/capabilities/rag.py`
- `modules/agents/adapters/tools.py` → `platform/capabilities/tools.py`
- `shared/llm.py` → `platform/llm.py`

**Registro de capacidades tipadas** en `platform/capabilities/registry.py`:
`Enum CapabilityKind {RAG, SEARCH, SCRAPE, FORMAT, PUBLISH, LLM}` + dataclass
`Capability(kind, name, description, entrypoint, available)` con resolución
perezosa del entrypoint (`"módulo:atributo"`, import absoluto) y funciones
`register() / get() / list_capabilities()`. Capacidades registradas de serie:

| Kind | Entrypoint | Disponible |
|------|-----------|------------|
| rag | `app.platform.capabilities.rag:semantic_search_context` | sí |
| search | `app.platform.capabilities.tools:ddg_search_with_urls` | sí |
| scrape | — (proveedor eliminado: `scraper.py` borrado en `71e3923`, SPEC-002 Superseded) | **no** |
| format | `app.modules.agents.adapters.paper_layout:build_paper_html` (referencia; se generaliza en T8.3) | sí |
| publish | `app.modules.agents.adapters.publicador:run_publicador` (referencia; se generaliza en T8.3) | sí |
| llm | `app.platform.llm:call_llm` | sí |

**Imports actualizados** en 13 ficheros consumidores (10 en `app/`, 3 en
`tests/`): `app.shared.llm` → `app.platform.llm`,
`app.modules.agents.adapters.rag` → `app.platform.capabilities.rag`, ídem
`tools`. Verificado a cero con grep (ver abajo).

**Decisiones documentadas:**
- `shared/qdrant.py` **se queda en `shared/`**: `rag.py` no lo usa (construye
  sus propias cabeceras HTTP); sus consumidores son `modules/ai/adapters/http.py`,
  `routers/ai.py` y `tests/test_qdrant_auth.py`. Moverlo no aporta a AC3.
- `doc_metadata.py` y los adapters de agente (investigador/redactor/revisor/
  formateador/publicador/generic/paper_layout) **no se mueven**: son la
  composición de AlejandrIA y corresponden a T8.3.
- `scrape` se declara como tipo **sin proveedor activo** (`available=False`):
  no se recrea el scraper eliminado; el registro es honesto con el estado real.
- Nombre `platform`: es subpaquete (`app.platform`) y no colisiona con el
  módulo stdlib `platform` porque todos los imports son absolutos; ninguno de
  los módulos movidos hace `import platform`.

**Test nuevo** `backend/tests/test_capabilities_registry.py` (5 tests): listar
capacidades cubre los 6 kinds; toda capacidad disponible resuelve a un
entrypoint importable e invocable; `scrape` figura como no disponible y su
`resolve()` lanza `CapabilityNotAvailable`; nombre desconocido → `KeyError`;
los módulos movidos viven bajo `app.platform` y las rutas legacy ya no existen.

### Definition of Done (AC3)
- [x] **AC3** — Existe `platform/capabilities/registry.py` con capacidades
  tipadas (rag/search/scrape/format/publish/llm) y la infraestructura (`rag`,
  `tools`, `llm`) vive bajo `platform/`, no bajo `modules/agents/adapters/`
  (`scraper` ya no existe; declarado como tipo sin proveedor). Listar
  capacidades funciona y está cubierto por tests.
- [x] Tests en verde (68 passed = 63 existentes + 5 nuevos, sin regresiones).
- [x] Sin secretos ni PII en el diff; no se commitearon `.db` ni artefactos.
- [x] Specs válidas (`scripts/validate_specs.py` OK); AC3 marcado `[x]` en
  SPEC-013.

### Verificación (comandos ejecutados)
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q`
  → **68 passed, 13 warnings**.
- `cd backend && DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -c "import app.main"`
  → `import app.main OK` (la app arranca).
- `grep -rn "shared.llm\|adapters.rag\|adapters.tools" backend/app backend/tests`
  → **sin coincidencias** (`adapters.doc_metadata` se queda, como corresponde).
- `python scripts/validate_specs.py` → `[OK] Specs SDD validas.`

### Fuera de alcance / notas
- **No** se re-cablea el orquestador para consumir capacidades: es T8.3
  (AC5/AC8, tests de paridad y feature flag). Las entradas `format`/`publish`
  del registro referencian los adapters actuales hasta entonces.
- Warning preexistente de SQLAlchemy en DROP por FK circular `projects↔users`
  (no relacionado con este cambio).
- Posible conflicto de merge con PRs en vuelo que importen `app.shared.llm` o
  `app.modules.agents.adapters.{rag,tools}`: resolver rebaseando sobre
  `develop` y aplicando el mismo mapeo de imports.
