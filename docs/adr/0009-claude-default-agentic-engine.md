# ADR-0009: Claude (Anthropic) como motor agéntico por defecto, multi-proveedor y multi-modelo por agente

- **Estado:** Propuesto
- **Fecha:** 2026-08-09
- **Decisores:** Equipo de plataforma
- **Relacionado:** ADR-0005 (motor vs paquetes de proyecto), ADR-0008 (memoria y
  presupuesto de contexto), SPEC-021 (contexto/memoria), SPEC-023 (spec de esta
  decisión)

## Contexto

El dispatcher único de LLM (`backend/app/platform/llm.py`) enruta por
`settings.LLM_PROVIDER` a **dos** proveedores: `ollama` (por defecto, on-prem) y
`openai` (SDK OpenAI, también compatible con Azure/vLLM/Groq/LM Studio vía
`OPENAI_BASE_URL`). El modelo por defecto lo resuelve `get_default_model()`
(`OLLAMA_MODEL` o `OPENAI_MODEL`) y cada agente puede sobreescribirlo con
`agent_settings[<agente>].model`, cuyo valor por defecto de UI sale del
frontmatter `model:` de `backend/app/agents/*.agent.md`.

Ese frontmatter hoy fija modelos **del namespace de Ollama** (investigador
`mistral:7b`; redactor/revisor `llama3.2:3b`; formateador `llama3.2:1b`;
orquestador/publicador `null` — no invocan LLM). Es decir, el "modelo por
agente" es **una sola cadena que asume el proveedor activo**: si se cambia el
proveedor por defecto, esas cadenas dejan de ser válidas.

Se decide que el producto use, **por defecto**, Claude (Anthropic) como motor
agéntico —con **modelos Claude distintos por agente según la necesidad**— y que
**por configuración** se pueda conmutar a Ollama, a otro motor compatible OpenAI
o a **modelos on-prem** cargados directamente (Ollama local, o servidor
compatible OpenAI como vLLM/LM Studio vía `OPENAI_BASE_URL`), sin tocar código.

Es una decisión **costosa de revertir** (cambia el proveedor por defecto, añade
una dependencia y un coste por token de API externa, y toca el contrato del
"modelo por agente"), por eso este ADR.

## Decisión

1. **Nuevo proveedor `anthropic`** en el dispatcher `platform/llm.py`, usando el
   **SDK oficial `anthropic`** (`AsyncAnthropic`) — nunca un shim OpenAI-compat
   contra Anthropic. Implementa las tres rutas ya existentes: generación simple,
   streaming y bucle de herramientas (`call_llm` / `call_llm_stream` /
   `call_llm_with_tools`). El mapeo de mensajes respeta el contrato de Anthropic
   (`system` como parámetro aparte, no como turno; `max_tokens` obligatorio).

2. **`LLM_PROVIDER` por defecto pasa a `anthropic`.** `ollama` y `openai`
   siguen siendo válidos y se seleccionan por configuración (env var o
   `config.yaml`). El on-prem "cargado directamente" se cubre con `ollama`
   (modelos locales) o con `openai` + `OPENAI_BASE_URL` (vLLM/LM Studio).

3. **Modelo por agente pasa a ser _consciente del proveedor_.** El frontmatter
   `.agent.md` gana un bloque `models:` mapeado por proveedor, además del `model:`
   legado (fallback). Resolución en cascada, de más a menos específico:
   `agent_settings[<agente>].model` (override explícito en UI/BD) →
   `.agent.md models[<proveedor activo>]` → `.agent.md model` (legado, solo si su
   namespace coincide con el proveedor) → `get_default_model()`.
   Así "los diferentes modelos por agente" conviven para Claude **y** para Ollama
   sin que un cambio de proveedor rompa la maqueta de modelos.

4. **Mapeo por defecto de modelos Claude por agente** (tiering por necesidad,
   calibrable con EDD/ADR-0006, no bloqueante en la spec):

   | Agente | Necesidad dominante | Modelo Claude por defecto |
   |--------|---------------------|---------------------------|
   | investigador | Investigación + síntesis + uso de herramientas/APIs | `claude-opus-5` |
   | redactor | Redacción académica larga (calidad/coste) | `claude-sonnet-5` |
   | revisor | Juicio crítico (puerta de calidad del bucle) | `claude-sonnet-5` |
   | formateador | Formateo/cita mecánico (rápido/barato) | `claude-haiku-4-5` |
   | orquestador / publicador | No invocan LLM | `null` |

   Default global del proveedor (`ANTHROPIC_MODEL`, usado por
   `get_default_model()` y por cualquier agente sin mapeo): **`claude-opus-5`**.

5. **Configuración nueva** (precedencia env > `config.yaml` > default): bloque
   `anthropic` con `ANTHROPIC_API_KEY` (obligatoria si el proveedor activo es
   `anthropic`), `ANTHROPIC_MODEL` (default `claude-opus-5`), `ANTHROPIC_BASE_URL`
   (opcional, para gateways/proxies) y `ANTHROPIC_MAX_TOKENS` (Anthropic exige
   `max_tokens`). La API key **nunca** se registra ni se expone en errores
   (mismo trato que `OPENAI_API_KEY`).

6. **Embeddings/RAG quedan desacoplados del proveedor de generación.** Anthropic
   **no** ofrece API de embeddings; el RAG (`nomic-embed-text` en Ollama /
   `text-embedding-3-small` en OpenAI) **no** cambia al poner `LLM_PROVIDER=anthropic`.
   Se documenta explícitamente que el proveedor de embeddings es independiente y
   sigue siendo Ollama/OpenAI (a futuro un `EMBED_PROVIDER` explícito; fuera del
   alcance mínimo de esta decisión).

7. **Adaptación de thinking/streaming (defaults del SDK oficial).** Para llamadas
   no triviales, thinking adaptativo (`thinking: {type: "adaptive"}`) en los
   modelos que lo soportan; streaming por defecto en respuestas largas
   (ya es el patrón del pipeline por SSE). Sin `budget_tokens` (deprecado/rechazado
   en la familia 5).

## Alternativas consideradas

- **Reescribir `llm.py` a Claude-only.** Rechazada: el requisito es explícitamente
  multi-proveedor (Claude por defecto, conmutable a Ollama/on-prem/otro). Un
  archivo Claude-only rompería el despliegue on-prem sin coste de API.
- **Claude vía capa OpenAI-compatible (`openai` + base_url de un gateway).**
  Rechazada como vía principal: el skill/estándar del repo exige el **SDK oficial
  de Anthropic** para código Claude; un shim OpenAI pierde thinking, el contrato
  nativo de herramientas y el manejo de errores propio.
- **Un único `model:` por agente reinterpretado por proveedor.** Rechazada: al
  conmutar proveedor, una cadena `mistral:7b` no tiene equivalente y caería
  siempre al default, perdiendo el tiering por agente. El bloque `models:` por
  proveedor lo preserva en ambos sentidos.
- **Seguir con Ollama por defecto.** Rechazada por decisión de producto: se quiere
  la calidad de Claude "out of the box"; on-prem pasa a ser el modo opt-in.

## Consecuencias

- (+) Calidad de Claude por defecto y **modelo adecuado por agente** (Opus donde
  hay razonamiento/tools, Sonnet en redacción/revisión, Haiku en formateo).
- (+) On-prem/soberanía de datos siguen soportados **por configuración**
  (`LLM_PROVIDER=ollama` o `openai`+`OPENAI_BASE_URL`), sin tocar código.
- (+) El "modelo por agente" deja de romperse al cambiar de proveedor (bloque
  `models:` por proveedor).
- (−) Nueva dependencia (`anthropic`) y **coste por token** de API externa cuando
  el proveedor activo es `anthropic`; se mitiga con el tiering (Haiku/Sonnet) y
  con el presupuesto de contexto de ADR-0008/SPEC-021.
- (−) Salida de datos a un tercero (Anthropic) en el modo por defecto: los
  despliegues con requisitos de soberanía deben conmutar a on-prem; se documenta
  en la spec y en `.env.example`.
- (~) Embeddings siguen dependiendo de Ollama/OpenAI aunque la generación sea
  Claude: un despliegue "solo Anthropic" necesita igualmente un proveedor de
  embeddings para el RAG. Documentado como consecuencia explícita.
