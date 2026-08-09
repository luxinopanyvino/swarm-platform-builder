# Tarea #255 — T12.2 Config del proveedor anthropic + LLM_PROVIDER por defecto anthropic + get_default_model

## 2026-08-09 16:19 — Completada ✅

- **Rama:** `feat/255-default-anthropic-provider`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #255`)
- **Spec/ADR:** SPEC-023, Épica E12, ADR-0009. Criterio vinculante: **AC2**.
- **Dependencias:** #254 (T12.1) — **cerrada y mergeada** (PR #259).

### Qué se hizo

Se hace de **Claude (Anthropic) el motor agéntico por defecto**, manteniendo la
**conmutación a on-prem por configuración** (sin tocar código). El *flip* del
default es una decisión notable, por eso va aislado en su propia tarea/PR.

**Precedencia de config (env > config.yaml > default del código).** Para que el
default efectivo sea `anthropic` había que alinear **las tres capas** — el default
del código no basta porque el `config.yaml` versionado lo sobreescribe:

1. **Default del código** (`core/config.py`): `LLM_PROVIDER` pasa de `"ollama"` a
   `"anthropic"` en el esquema `Settings` **y** en el *fallback* de
   `_build_settings` (`.get("provider", "anthropic")`).
2. **`config.yaml`** (raíz) y **`backend/config.yaml`** (el que carga el backend al
   correr desde `backend/`): `llm.provider: anthropic` + nuevo bloque `anthropic:`
   (`api_key: ''`, `model: claude-opus-5`, `base_url: null`, `max_tokens: 4096`)
   con comentarios de cómo **volver a on-prem** (`ollama`/`openai`) y de que la
   API key se inyecta por env (`ANTHROPIC_API_KEY`, mayor prioridad).

`get_default_model()` ya resolvía `ANTHROPIC_MODEL` para el proveedor `anthropic`
(landeado en T12.1); aquí queda validado por AC2.

**Conmutación garantizada:** la variable de entorno `LLM_PROVIDER` (máxima
prioridad) cambia a `ollama`/`openai` sin tocar código ni ficheros.

### Decisiones documentadas

- **Había dos `config.yaml`** (`./config.yaml` y `./backend/config.yaml`, este
  último es el que gana al correr desde `backend/`). Se actualizan **ambos** para
  evitar que el default efectivo dependa del *cwd*.
- **Coste/UX en dev:** con el default en `anthropic`, un arranque local sin
  `ANTHROPIC_API_KEY` falla en la **primera** llamada al LLM (error perezoso de
  T12.1), no en el arranque. El camino on-prem (Ollama de `dev-local.cmd`) sigue a
  un `LLM_PROVIDER=ollama` de distancia; documentado en los comentarios del yaml.
- **Embeddings**: sin cambios; Anthropic no ofrece API de embeddings (nota en el
  yaml). Los `.env.example` y el mapeo por agente llegan en T12.3/T12.4.

### Test nuevo

`backend/tests/test_llm_provider_default.py` (7 casos):
- default del **esquema** (`Settings().LLM_PROVIDER == "anthropic"`,
  `ANTHROPIC_MODEL == "claude-opus-5"`, `ANTHROPIC_MAX_TOKENS == 4096`);
- default **efectivo** de `_build_settings()` (con el `config.yaml` versionado) =
  `anthropic`;
- `get_default_model()` sigue al proveedor activo (anthropic→ANTHROPIC_MODEL,
  ollama→OLLAMA_MODEL, openai→OPENAI_MODEL);
- **conmutación por env** sin tocar código: `LLM_PROVIDER=ollama|openai` gana al
  `config.yaml`.

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest \
    tests/test_llm_provider_default.py tests/test_llm_anthropic.py \
    tests/test_llm_retry.py -q                                   # → 24 passed

# default efectivo y rollback por env
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -c \
  "import app.platform.llm as l; from app.core.config import settings; \
   print(settings.LLM_PROVIDER, l.get_default_model())"          # anthropic claude-opus-5
DEBUG=true SECRET_KEY=ci-secret-not-for-prod LLM_PROVIDER=ollama python -c \
  "import app.platform.llm as l; print(l.get_default_model())"   # mistral:7b
```

### Definition of Done (AC2)

- [x] **AC2** — sin overrides, `LLM_PROVIDER == "anthropic"` y
  `get_default_model() == ANTHROPIC_MODEL` (`claude-opus-5`); con
  `LLM_PROVIDER=ollama`/`openai` el enrutado y el default vuelven a ese proveedor
  **sin cambios de código**. Verificado por tests.
- [x] Tests que cubren el cambio, en verde (24 passed junto a los de T12.1).
- [x] Sin secretos ni PII en el diff (las `api_key` del yaml quedan vacías; la
  clave se inyecta por env).
- [x] Config documentada (comentarios de conmutación en ambos `config.yaml`).
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.
