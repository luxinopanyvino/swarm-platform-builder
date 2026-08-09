# Tarea #254 — T12.1 Proveedor anthropic en el dispatcher (SDK oficial: generación, streaming, tools)

## 2026-08-09 16:05 — Completada ✅

- **Rama:** `feat/254-anthropic-provider`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #254`)
- **Spec/ADR:** SPEC-023 (Claude por defecto como motor agéntico), Épica E12,
  ADR-0009. Criterios vinculantes de T12.1: **AC1** y **AC5**.
- **Dependencias:** Ninguna.

### Qué se hizo

Se añadió el proveedor **`anthropic`** al dispatcher único de LLM
(`backend/app/platform/llm.py`), usando el **SDK oficial `anthropic`**
(`AsyncAnthropic`) — nunca un shim OpenAI-compat contra Anthropic.

**Enrutado (`platform/llm.py`).** Las tres entradas del dispatcher ganan una rama
`provider == "anthropic"`:
- `call_llm` → `_call_anthropic` (generación simple).
- `call_llm_stream` → `_call_anthropic_stream` (streaming de deltas de texto).
- `call_llm_with_tools` → `_tool_loop_anthropic` (bucle agéntico de herramientas).
- `get_default_model()` añade el caso `anthropic` → `settings.ANTHROPIC_MODEL`.

**Contrato nativo de Anthropic** (no OpenAI):
- `system_prompt` se mapea al parámetro **`system`** de nivel superior (Claude no
  usa un *turno* system), no como mensaje.
- `max_tokens` es **obligatorio**; se fija con `ANTHROPIC_MAX_TOKENS` (default 4096,
  sobreescribible por llamada/agente).
- El texto de la respuesta se extrae concatenando los **bloques de contenido**
  `type == "text"` (`_anthropic_text`), tolerando bloques `thinking` futuros.
- Herramientas: `_to_anthropic_tools` convierte los esquemas estilo OpenAI/Ollama
  (`{"type":"function","function":{name,description,parameters}}`) al formato
  Anthropic (`{name, description, input_schema}`); los esquemas ya nativos pasan
  tal cual. El bucle reenvía los bloques `tool_use` → ejecuta `tool_executor` →
  responde con bloques `tool_result` hasta que `stop_reason != "tool_use"`.

**Clasificación de errores** (`_classify_anthropic_error`), reutilizando la capa
de resiliencia existente (`_retry_async`/`_retry_stream`, backoff + jitter):
- `AuthenticationError` (401) → **permanente** (`RuntimeError`), **sin** interpolar
  la excepción → la API key **nunca** aparece en el mensaje.
- `RateLimitError` (429), `APIConnectionError`/timeout, `APIStatusError` con
  `status >= 500` → **transitorio** (`TransientLLMError`, reintentable).
- `APIStatusError`/`APIError` 4xx → **permanente**.
- Respuesta vacía → transitorio (modelo calentando), coherente con Ollama/OpenAI.

**Error perezoso por falta de key** (`_require_anthropic_key`): con
`LLM_PROVIDER=anthropic` **sin** `ANTHROPIC_API_KEY`, el arranque **no** falla; la
**primera** llamada al LLM lanza `RuntimeError` permanente (sin reintento, sin la
key en el mensaje).

**Config (`core/config.py`).** Bloque `anthropic` en `Settings` y en
`_build_settings` con precedencia env > `config.yaml` > default:
`ANTHROPIC_API_KEY=""`, `ANTHROPIC_MODEL="claude-opus-5"`, `ANTHROPIC_BASE_URL=None`
(gateway/proxy opcional), `ANTHROPIC_MAX_TOKENS=4096`. La key nunca se registra.

**Dependencia:** `anthropic>=0.40.0` en `backend/requirements.txt`.

### Alcance y límites (deja para otras tareas de E12)

- **`LLM_PROVIDER` sigue en `"ollama"` por defecto.** El *flip* del default a
  `anthropic` (para que Claude sea el motor "out of the box") es **T12.2** (AC2),
  aislado a propósito por ser la decisión notable/costosa de revertir.
- **Modelo por agente consciente del proveedor** (bloque `models:` + cascada) es
  **T12.3** (AC3/AC4); aquí el proveedor resuelve el modelo con
  `get_default_model()` o el `model` explícito que ya pasan los adapters.
- **Mapeo por agente en `.agent.md` y docs `.env.example`** es **T12.4**.
- **Thinking adaptativo**: no se envía en T12.1 para evitar `400` en modelos que
  no lo soporten; se habilitará por config junto al mapeo por agente.

### Decisiones documentadas

- `get_default_model()` incluye el caso `anthropic` ya en T12.1 (es intrínseco a
  "el proveedor existe en el dispatcher"); T12.2 valida el default global y hace
  el *flip*. Solapamiento mínimo y deliberado para que cada PR sea coherente.
- Embeddings/RAG **no** se tocan: Anthropic no ofrece API de embeddings; el RAG
  sigue en Ollama/OpenAI aunque la generación sea Claude (se documenta en T12.4).

### Test nuevo

`backend/tests/test_llm_anthropic.py` (12 tests) — sin LLM real ni el paquete
`anthropic` instalado: se inyecta un módulo `anthropic` falso en `sys.modules`
que replica la jerarquía de errores del SDK. Cubre:
- **AC1**: mapeo `system`/`max_tokens`/`messages`/modelo y extracción de texto;
  enrutado de `call_llm` a anthropic con el modelo por defecto; streaming de
  deltas; bucle de herramientas (tool_use → ejecución → texto final); conversión
  de esquemas de herramientas.
- **AC5**: falta de key = permanente y perezoso; `AuthenticationError` permanente
  **sin filtrar la key**; 429/conexión/5xx transitorios; 4xx permanente;
  respuesta vacía transitoria.

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest \
    tests/test_llm_anthropic.py tests/test_llm_retry.py -q
# → 17 passed

# sanidad de config/enrutado
DEBUG=true SECRET_KEY=ci-secret-not-for-prod ANTHROPIC_API_KEY=sk-test \
    LLM_PROVIDER=anthropic python -c "import app.platform.llm as l; \
    print(l.get_default_model())"   # → claude-opus-5

python -m py_compile app/platform/llm.py app/core/config.py  # OK
```

### Definition of Done (T12.1)

- [x] **AC1** — `LLM_PROVIDER="anthropic"` enruta `call_llm`/`call_llm_stream`/
  `call_llm_with_tools` al SDK oficial (`AsyncAnthropic`), con `system` como
  parámetro y `max_tokens` fijado. Verificado por test (SDK mockeado).
- [x] **AC5** — 401 permanente sin key en el mensaje; 429/5xx/timeout/conexión
  transitorios (retry con backoff existente); falta de key = error perezoso
  permanente en la primera llamada. Verificado por test.
- [x] Tests que cubren el cambio, en verde (17 passed).
- [x] Sin secretos ni PII en el diff; la API key nunca se registra ni se expone.
- [x] Docs de la decisión (ADR-0009/SPEC-023) ya existentes; bitácora añadida.
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.
