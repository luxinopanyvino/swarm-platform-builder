# Tarea #256 — T12.3 Resolución de modelo por agente consciente del proveedor (bloque models: + cascada)

## 2026-08-09 16:32 — Completada ✅

- **Rama:** `feat/256-provider-aware-agent-model`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #256`)
- **Spec/ADR:** SPEC-023, Épica E12, ADR-0009. Criterios vinculantes: **AC3** y **AC4**.
- **Dependencias:** #255 (T12.2) — **cerrada y mergeada** (PR #260).

### Qué se hizo

El "modelo por agente" pasa a ser **consciente del proveedor activo**, para que el
tiering por agente sobreviva al conmutar de motor (Claude ↔ Ollama ↔ OpenAI).

**Utilidad central** `resolve_agent_model(agent_name, agent_settings)` en
`platform/llm.py`, con la **cascada** (más específico gana):

1. `agent_settings[<agente>].model` — override explícito (UI/BD), respetado **solo
   si su namespace coincide** con el proveedor activo. Así un valor legado de
   Ollama seeded en la BD **no secuestra** un despliegue Claude/OpenAI.
2. `.agent.md` `models[<proveedor>]` — default por agente y proveedor.
3. `.agent.md` `model` legado — solo si su namespace coincide con el proveedor.
4. `get_default_model()` — default global del proveedor.

Helpers: `_model_namespace()` (claude*→anthropic; gpt*/o1*/o3*/text-*→openai; resto,
incl. tags on-prem `mistral:7b`/`llama3.2:3b`, →ollama) y `_load_agent_frontmatter()`.

**Bloque `models:` en los 4 `.agent.md`** (conservando `model:` legado como
fallback Ollama):

| Agente | anthropic | ollama (legado) |
|--------|-----------|-----------------|
| investigador | `claude-opus-5` | `mistral:7b` |
| redactor | `claude-sonnet-5` | `llama3.2:3b` |
| revisor | `claude-sonnet-5` | `llama3.2:3b` |
| formateador | `claude-haiku-4-5` | `llama3.2:1b` |

**Adapters** (`redactor`, `revisor`, `formateador`, `investigador`): dejan de hacer
`agent_cfg.get("model") or get_default_model()` y pasan a
`resolve_agent_model("<agente>", state.get("agent_settings"))`.

**Corrección de un latente introducido por el default Claude (T12.2):** el
Investigador usaba un modelo ligero **hardcodeado** (`llama3.2:1b`) para la síntesis
sin fuentes (evita OOM de VRAM en Ollama). Ese string es de Ollama; ahora **solo**
se aplica cuando `LLM_PROVIDER == "ollama"` — en la nube se mantiene el modelo
resuelto (no hay VRAM local y no se puede mandar un id de Ollama a Anthropic).

### Decisiones y límites

- **Guard de namespace en el paso 1:** desviación deliberada y documentada del
  AC3 literal (que lista `agent_settings.model` sin condición). Es necesaria
  porque la BD siembra `model` desde el `.agent.md model:` legado (Ollama); sin el
  guard, bajo `anthropic` todos los agentes recibirían el modelo Ollama y AC4
  fallaría. El comportamiento resultante es el pretendido por la spec ("el más
  específico **para el proveedor** gana").
- **`generic.py` (agentes custom) queda fuera de AC4:** sigue usando
  `load_agent_profile().model`. Un agente custom bajo `anthropic` sin un `models:`
  propio recibiría su `model:` legado; se documenta como **seguimiento** (añadir la
  misma cascada a los custom, o exigir `models:` en su `.agent.md`). AC3/AC4 cubren
  los 4 agentes del núcleo.
- Sin migraciones de BD (SPEC-023 §7): el `models:` vive en el `.agent.md`, leído
  por el resolutor; el `agent_settings` sigue siendo el dict actual.

### Test nuevo

`backend/tests/test_llm_agent_model_resolution.py` (13 casos):
- **AC4**: los 4 agentes mapean a su modelo Claude bajo `anthropic`.
- **AC3**: mismo agente → modelo distinto por proveedor (investigador:
  anthropic→opus-5 vs ollama→mistral:7b).
- cascada: override honrado si el namespace coincide; **legado Ollama ignorado**
  bajo anthropic (→ `models[anthropic]`); fallback al default global cuando no hay
  `models[proveedor]` ni legado del namespace correcto; agente inexistente →
  default; detección de namespace por prefijo.

### Verificación

```
# desde backend/
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest \
    tests/test_llm_agent_model_resolution.py tests/test_llm_provider_default.py \
    tests/test_llm_anthropic.py tests/test_llm_retry.py -q          # → 40 passed

# resolución end-to-end por proveedor
LLM_PROVIDER=anthropic → investigador=claude-opus-5, redactor/revisor=claude-sonnet-5,
                         formateador=claude-haiku-4-5
LLM_PROVIDER=ollama    → investigador=mistral:7b, redactor/revisor=llama3.2:3b,
                         formateador=llama3.2:1b
python -m py_compile (llm.py + 4 adapters)                          # OK
```

### Definition of Done (AC3, AC4)

- [x] **AC3** — cascada `agent_settings.model → models[proveedor] → legado
  (namespace) → get_default_model()`; mismo agente resuelve distinto por proveedor.
  Verificado por tests.
- [x] **AC4** — mapeo por defecto anthropic por agente (opus/sonnet/haiku);
  orquestador/publicador siguen sin invocar LLM. Verificado por tests.
- [x] Tests que cubren el cambio, en verde (40 passed con los de T12.1/T12.2).
- [x] Sin secretos ni PII en el diff.
- [x] Rama con prefijo `feat/` hacia `develop`, sin push directo.
