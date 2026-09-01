# Tarea #172 — T5.2 Métricas Prometheus (latencia, errores, tokens LLM)

## 2026-08-30 16:05 — Completada ✅

- **Rama:** `feat/172-prometheus-metrics`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #172`)
- **Spec/ADR:** SPEC-019, Épica E5. Criterio vinculante: **AC2**.
- **Dependencias:** ninguna. Se apoya en T5.1 (logging) y T5.4 (router de salud),
  ambas mergeadas.

### Qué se hizo

`app/platform/metrics.py` y `GET /metrics`, con lo que pide AC2:

```
http_requests_total{method="GET",route="/health",status="200"} 1.0
http_requests_total{method="GET",route="/api/v1/articles/{article_id}",status="401"} 1.0
llm_request_duration_seconds_count{agent="redactor",model="claude-opus-5",provider="anthropic"} 1.0
llm_tokens_total{agent="redactor",direction="input",model="claude-opus-5",provider="anthropic"} 1840.0
llm_tokens_total{agent="redactor",direction="output",model="claude-opus-5",provider="anthropic"} 920.0
```

### La decisión de diseño: cardinalidad

Fíjate en la segunda línea: `route="/api/v1/articles/{article_id}"`, **no** la URL
con el UUID. Es lo que más importa de esta tarea.

Una etiqueta con la URL concreta crea **una serie temporal por artículo**.
Prometheus las guarda todas, para siempre, y la instancia acaba inservible por
culpa de la propia instrumentación. Y el fallo no aparece en desarrollo —donde hay
tres artículos— sino meses después en producción.

Se usa la plantilla de ruta, que es un conjunto pequeño y fijo, y cuando no se
puede resolver —un `404`, o un error antes de enrutar— se etiqueta `unmatched` en
lugar de dejar entrar la URL cruda. Ese segundo caso importa: una ruta inventada
sería el vector más fácil para reventar la cardinalidad **desde fuera**. Hay tests
para ambos.

### Otras decisiones

- **Los tokens se leen dentro de cada proveedor**, que es el único sitio donde se
  saben: la respuesta de la API los trae y `call_llm` solo ve el texto ya extraído.
  Instrumentados Ollama (normal y streaming, del chunk `done`), Anthropic (normal y
  streaming, del mensaje final) y OpenAI (normal).
- **El streaming de OpenAI se queda sin recuento de tokens, y se dice.** Requiere
  `stream_options={"include_usage": True}`, y esa ruta admite `OPENAI_BASE_URL`:
  las pasarelas compatibles con OpenAI a menudo rechazan ese parámetro. **Una
  llamada rota es peor que una métrica ausente.** La latencia sí se mide, como en
  el resto. Está anotado en el código y hay un test que lo vigila.
- **El agente se etiqueta con un `ContextVar`**, fijado en `make_node_wrapper`.
  Es el único punto por el que pasan **todos** los agentes —incluidos los dinámicos
  de `.agent.md`—, así que uno nuevo queda etiquetado sin tocar nada; la
  alternativa era arrastrar el nombre por `call_llm` → `_retry_async` →
  `_call_<proveedor>`. Mismo patrón que el `request_id_ctx` de T5.1.
- **`observe_llm_tokens` está separada de `observe_llm_call`** por un fallo que me
  encontré a mí mismo: la primera versión reportaba los tokens llamando a
  `observe_llm_call`, lo que habría incrementado `llm_requests_total` **dos veces
  por llamada**. Los tokens se conocen dentro del proveedor y la duración fuera, así
  que son dos funciones.
- **La latencia se mide envolviendo el dispatcher entero**, reintentos incluidos:
  es lo que de verdad espera quien llama, y un proveedor que solo responde al
  tercer intento tiene que verse lento, no sano.
- **Cubetas distintas para HTTP y LLM.** Reusar las de HTTP (hasta 10 s) dejaría
  casi toda llamada a un modelo en el cubo `+Inf` y los cuantiles no dirían nada.
- **El cronómetro HTTP para en `finally`**, así que una excepción también cuenta.
  Si solo se midieran las respuestas correctas, la latencia parecería **mejorar**
  justo cuando el servicio empieza a fallar.
- **Medir nunca lanza**: si el registro falla, se traga el error. Una métrica rota
  no puede tumbar una generación. Hay test.
- **`/metrics` va sin autenticación**, como `/health`: quien la consulta es el
  recolector, que no tiene credenciales. No queda expuesta al exterior porque nginx
  solo hace de pasarela para `/api/` (T3.4); hay un test que lo comprueba, para que
  publicarla algún día obligue a decidir cómo protegerla.

### Test nuevo

`backend/tests/test_metrics.py` (19 casos): el endpoint responde en formato de
exposición y sin autenticación, y no está publicado por nginx; se cuentan método,
ruta y estado, y también los `4xx` —«errores por endpoint» sale de la etiqueta
`status`, no de un contador aparte—; **dos artículos distintos comparten serie** y
una ruta inventada no filtra su URL; la latencia y los tokens de LLM llevan
proveedor, modelo y agente, con dirección `input`/`output`; una llamada fallida se
cuenta con su estado; el agente sale del contexto cuando no se pasa, y sin contexto
la etiqueta es `none` explícito —una etiqueta ausente rompe las consultas—; medir
no lanza aunque el registro esté roto; y los proveedores instrumentados, el hueco
documentado de OpenAI y las cubetas separadas.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_metrics.py -q
# → 19 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 558 passed
python scripts/validate_specs.py   # → [OK]
```

El lock se recompiló con `prometheus-client` y se verificó instalándolo en un venv
limpio de Python 3.12: **558 passed** con las versiones exactas.

### Definition of Done (AC2)

- [x] **AC2** — `/metrics` expone latencia y errores por endpoint y tokens/latencia
  de LLM por agente y modelo, en formato Prometheus.
- [x] Tests que cubren el cambio, en verde (19 nuevos; 558 en la suite).
- [x] Docs: **AC1, AC2 y AC4 marcados en SPEC-019**; los porqués viven en el
  docstring del módulo.
- [x] Sin secretos en el diff; dependencia nueva pineada con hash.
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

- **Varios workers**: `prometheus_client` guarda los contadores en memoria del
  proceso, así que con varios workers cada uno reporta lo suyo. `render_metrics`
  ya agrega entre procesos si se define `PROMETHEUS_MULTIPROC_DIR`, pero **el
  compose no la define todavía**: hacerlo requiere un directorio compartido y
  limpiarlo al arrancar, y encaja mejor cuando se suba de verdad el número de
  workers (ver el seguimiento de #170).
- De **E5** queda **#173 (T5.3, tracing OpenTelemetry)**, marcada como fase 2 y de
  severidad baja. Con ella, la épica quedaría completa.
