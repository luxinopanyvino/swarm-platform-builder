# ADR-0004: Observabilidad mínima y CI/CD con escaneo de cadena de suministro

- **Estado:** Propuesto
- **Fecha:** 2026-06-26
- **Decisores:** Equipo de plataforma, Operaciones

## Contexto

No hay pipeline de CI (`.github/workflows` ausente), las dependencias no están
pineadas, y la observabilidad se limita a logs de texto con emojis y a la tabla
`agent_runs`. No hay métricas, tracing, ni *health checks* de readiness. Esto
impide detectar regresiones, medir latencia/errores/uso de tokens LLM y operar
con confianza.

## Decisión

1. **CI obligatorio** en cada PR: lint, `pytest`, build del frontend y
   escaneo de dependencias (`pip-audit`, `npm audit`), con Dependabot activo.
2. **Observabilidad mínima:**
   - logging **estructurado** (JSON) con `request_id`/`correlation_id`,
   - métricas **Prometheus** (latencia HTTP, tasa de error, duración de
     pipeline, tokens LLM por agente),
   - `/health` con distinción **liveness/readiness** y chequeo de dependencias
     (DB, Qdrant, Ollama),
   - tracing **OpenTelemetry** (objetivo, fase 2).
3. **Dependencias pineadas** con lockfile/hashes para builds reproducibles.

## Alternativas consideradas

- **Solo logs** — insuficiente para diagnóstico y SLOs.
- **APM SaaS desde el día 1** — coste/complejidad; empezamos con stack abierto
  (Prometheus/OTel) compatible on-prem, coherente con el resto del sistema.

## Consecuencias

- **Positivas:** detección temprana de fallos, métricas para SLOs, builds
  reproducibles, defensa de cadena de suministro.
- **Negativas / coste:** instrumentación y mantenimiento del pipeline.
- **Seguimiento:** épicas E5 (observabilidad) y E6 (gobernanza/CI) del backlog.
