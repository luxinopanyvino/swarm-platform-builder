# Tarea #257 — T12.4 Mapeo de modelos Claude por agente en .agent.md + docs (.env.example/config.yaml)

## 2026-08-09 16:38 — Completada ✅

- **Rama:** `feat/257-anthropic-docs-embeddings`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #257`)
- **Spec/ADR:** SPEC-023, Épica E12, ADR-0009. Criterios vinculantes: **AC4** y **AC6**.
- **Dependencias:** #256 (T12.3) — **cerrada y mergeada** (PR #261).

### Qué se hizo

Cierra la parte de **documentación/configuración** del motor Claude y verifica el
**desacople de embeddings**.

**AC4 — mapeo por agente.** Los bloques `models:` en los 4 `.agent.md`
(investigador→opus-5, redactor/revisor→sonnet-5, formateador→haiku-4-5) y el bloque
`anthropic:` de `config.yaml` **ya se añadieron** en T12.3 y T12.2 respectivamente;
aquí se referencian y se completa su documentación en `.env.example`.

**Docs — `.env.example` (raíz y `backend/`, ambos idénticos):** nueva sección de
proveedor LLM y bloques por proveedor:
- `LLM_PROVIDER=anthropic` (default) con nota de conmutación a `ollama`/`openai`
  (vLLM/LM Studio vía `OPENAI_BASE_URL`) sin cambios de código.
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL=claude-opus-5` / `ANTHROPIC_BASE_URL` /
  `ANTHROPIC_MAX_TOKENS=4096`, con nota de error perezoso si falta la key.
- OpenAI (comentado, solo si `LLM_PROVIDER=openai`).
- `OLLAMA_EMBED_MODEL=nomic-embed-text` con nota explícita de que **los embeddings
  son independientes del motor** (ver AC6).

**AC6 — embeddings desacoplados.** El selector `get_embedding` de
`platform/capabilities/rag.py` usa OpenAI **solo** cuando `LLM_PROVIDER=="openai"`;
en cualquier otro caso — **incluido `anthropic`** — usa Ollama, porque Anthropic
**no** ofrece API de embeddings. Se aclaró el docstring para dejarlo explícito.
Comportamiento verificado: conmutar el motor a Claude nunca enruta un embedding a
Anthropic ni rompe el RAG.

### Alcance

- No se toca `config.yaml` (su bloque `anthropic` llegó en T12.2) ni los `.agent.md`
  (sus `models:` llegaron en T12.3): esta tarea es docs + verificación de AC6.
- El posible `EMBED_PROVIDER` explícito sigue fuera de alcance (SPEC-023 §2).

### Test nuevo

`backend/tests/test_rag_embeddings_provider_decoupled.py` (3 casos): con
`LLM_PROVIDER` en `anthropic`/`ollama`/`openai`, el enrutado de `get_embedding`
(espías sobre `_get_embedding_ollama`/`_get_embedding_openai`) es
ollama/ollama/openai respectivamente — nunca Anthropic.

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest \
  tests/test_rag_embeddings_provider_decoupled.py \
  tests/test_llm_agent_model_resolution.py tests/test_llm_provider_default.py \
  tests/test_llm_anthropic.py tests/test_llm_retry.py -q             # → 43 passed

diff .env.example backend/.env.example                                # idénticos
```

### Definition of Done (AC4, AC6)

- [x] **AC4** — `.agent.md` con `models:` por proveedor (landeado en T12.3) +
  documentado en `.env.example`.
- [x] **AC6** — embeddings/RAG independientes de `LLM_PROVIDER`: `anthropic` usa
  Ollama (Anthropic no tiene embeddings), documentado en `.env.example` y el
  docstring, y verificado por tests.
- [x] Tests que cubren el cambio, en verde (43 passed).
- [x] Sin secretos ni PII en el diff (`.env.example` con valores vacíos).
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.
