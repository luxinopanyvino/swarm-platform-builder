# Tarea #258 — T12.5 Tests del proveedor anthropic, cascada de resolución y clasificación de errores

## 2026-08-09 17:30 — Completada ✅

- **Rama:** `feat/258-anthropic-coverage-closing`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #258`)
- **Spec/ADR:** SPEC-023, Épica E12, ADR-0009. Criterio vinculante: **AC7**.
- **Dependencias:** #256/#257 (T12.3/T12.4) — **cerradas y mergeadas** (#261/#262).

### Qué se hizo

Tarea de **cierre** de E12. Cada tarea anterior aportó sus propios tests, de modo
que AC1–AC6 ya estaban cubiertos; aquí se **audita** la cobertura, se rellena el
**único hueco real** y se deja el **mapa AC→test**.

**Hueco cubierto:** la API pública `call_llm_stream` enrutando a la rama
**anthropic a través del wrapper de retry** (`_retry_stream`). Hasta ahora solo se
probaba `_call_anthropic_stream` directamente. Nuevo
`backend/tests/test_llm_anthropic_stream_routing.py` (2 casos):
- `call_llm_stream` (proveedor anthropic) enruta a `_call_anthropic_stream` con el
  modelo por defecto (`claude-opus-5`) y emite los deltas;
- un fallo de conexión **antes del primer token** se reintenta en la ruta anthropic
  (retry con backoff cero en test).

### Mapa de cobertura AC1–AC7 (sin LLM real; SDK `anthropic` mockeado)

| AC | Qué verifica | Test(s) |
|----|--------------|---------|
| **AC1** | Enrutado al SDK oficial; `system` como parámetro, `max_tokens` fijado; streaming y bucle de tools | `test_llm_anthropic.py` (maps_system_and_max_tokens, routes_to_anthropic, stream_yields_text_deltas, tool_loop_executes_tool, to_anthropic_tools) + `test_llm_anthropic_stream_routing.py` (stream routing) |
| **AC2** | Default `anthropic`; `get_default_model()` por proveedor; conmutación por env | `test_llm_provider_default.py` (5) |
| **AC3** | Cascada de resolución; mismo agente → modelo distinto por proveedor | `test_llm_agent_model_resolution.py` (cascada, override, distinct-per-provider) |
| **AC4** | Mapeo Claude por agente (opus/sonnet/haiku) | `test_llm_agent_model_resolution.py` (mapping_per_agent, ignores_legacy) |
| **AC5** | 401 permanente sin filtrar la key; 429/5xx/timeout transitorios; falta de key = error perezoso | `test_llm_anthropic.py` (missing_key, auth_error, transient_errors, 4xx, empty_response) |
| **AC6** | Embeddings independientes del motor (anthropic→Ollama, nunca Anthropic) | `test_rag_embeddings_provider_decoupled.py` (3) |
| **AC7** | Existen tests que cubren AC1–AC6 sin LLM real | **este mapa** + la suite completa (45 passed) |

### Verificación

```
# desde backend/  — toda la suite E12
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest \
  tests/test_llm_anthropic_stream_routing.py tests/test_llm_anthropic.py \
  tests/test_llm_provider_default.py tests/test_llm_agent_model_resolution.py \
  tests/test_rag_embeddings_provider_decoupled.py tests/test_llm_retry.py -q
# → 45 passed
```

### Definition of Done (AC7)

- [x] **AC7** — tests que cubren AC1–AC6 sin LLM real (SDK mockeado), incluidos el
  mapeo de mensajes (system/max_tokens), la cascada de resolución por proveedor y
  la clasificación de errores; hueco de `call_llm_stream`→anthropic cerrado.
- [x] Suite E12 en verde (45 passed).
- [x] Sin secretos ni PII en el diff.
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.

### Cierre de la épica E12

Con T12.5, **E12 (Motor LLM multi-proveedor, Claude por defecto) queda completa**:
proveedor `anthropic` (T12.1), default Claude conmutable (T12.2), modelo por agente
consciente del proveedor (T12.3), docs + embeddings desacoplados (T12.4) y cobertura
de cierre (T12.5).

**Seguimiento anotado (fuera de E12):** `generic.py` (agentes custom) aún no es
provider-aware; posible `EMBED_PROVIDER` explícito; y la infra de CI necesita el
secret `ANTHROPIC_API_KEY` para el job `Claude · revisar PR`.
