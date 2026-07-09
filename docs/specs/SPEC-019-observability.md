# SPEC-019: Observabilidad del backend y del pipeline

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E5 (Observabilidad)
- **ADR relacionado:** ADR-0004
- **Severidad:** 🟡

> Adopta formalmente las tareas T5.1–T5.4 sembradas por el bootstrap sin spec.
> T5.1 es además prerequisito de la traza de explicabilidad de E9
> ([SPEC-014](SPEC-014-explainability-and-edd.md), T9.1).

## 1. Problema

Los logs son texto libre con emojis y sin `request_id`, imposibles de agregar
o correlacionar; no hay métricas más allá de la tabla `agent_runs`; no hay
tracing distribuido; y `/health` es trivial (no comprueba DB, Qdrant ni
Ollama), por lo que un despliegue "sano" puede estar roto.

## 2. Objetivos / No-objetivos

- **Objetivos:** logs JSON correlacionables, métricas Prometheus de API y LLM,
  tracing por request/paso de agente (fase 2) y health real de dependencias.
- **No-objetivos:** desplegar el stack de observación (Grafana/Loki/Tempo);
  alerting.

## 3. Criterios de aceptación

- [ ] **AC1** — *Given* cualquier request o paso de pipeline, *When* se
  loguea, *Then* la salida es **JSON estructurado** con `timestamp`, `level`,
  `logger`, `request_id`/correlation id (propagado por middleware) y campos
  contextuales; sin emojis en nivel INFO+.
- [ ] **AC2** — *Given* el backend en marcha, *When* se consulta `/metrics`,
  *Then* expone en formato Prometheus latencia y errores por endpoint y
  contadores de tokens/latencia LLM por agente y modelo.
- [ ] **AC3** — *Given* una ejecución de pipeline, *When* el tracing OTel está
  habilitado, *Then* cada request y cada paso de agente genera spans anidados
  exportables por OTLP (activable por configuración, apagado por defecto).
- [ ] **AC4** — *Given* `/health`, *Then* distingue **liveness** (proceso vivo)
  de **readiness** (DB, Qdrant y Ollama alcanzables), devolviendo `503` con el
  detalle de la dependencia caída cuando no está listo.

## 4. Diseño propuesto

AC1: `logging.config` con formatter JSON + middleware ASGI de correlación
(sustituye los logs con emoji de `use_cases.py`/routers). AC2:
`prometheus-client` con instrumentación en middleware y en el dispatcher LLM
(`app/platform/llm.py` tras T8.2, que ya conoce tokens/modelo). AC3: `opentelemetry-sdk`
opcional tras AC1. AC4: extender el `/health` de `app/main.py` con chequeos
`asyncio.gather` + timeout corto por dependencia.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Verbosidad JSON encarece logs en dev | Bajo | Formatter humano cuando `DEBUG=true` |
| Readiness estricta tumba pods sanos por deps lentas | Medio | Timeouts cortos + caché breve del resultado |

## 6. Plan de pruebas

Unit del formatter/middleware (log capturado es JSON válido con request_id);
e2e de `/metrics` (labels esperadas) y `/health` (200/503 con deps mockeadas).

## 7. Impacto operativo / observabilidad

Esta spec **es** la base de observabilidad; T9.1 (SPEC-014) consume su
correlación para la traza de explicabilidad.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E5
  title: "Observabilidad"
  area: area/observability
tasks:
  - id: T5.1
    title: Logging estructurado (JSON) + correlation IDs
    sev: medium
    depends_on: []
    acceptance: [AC1]
  - id: T5.2
    title: Métricas Prometheus (latencia, errores, tokens LLM)
    sev: medium
    depends_on: [T5.1]
    acceptance: [AC2]
  - id: T5.3
    title: Tracing OpenTelemetry (fase 2)
    sev: low
    depends_on: [T5.1]
    acceptance: [AC3]
  - id: T5.4
    title: /health liveness/readiness con chequeo de dependencias
    sev: medium
    depends_on: []
    acceptance: [AC4]
```
