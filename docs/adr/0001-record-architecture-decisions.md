# ADR-0001: Registrar decisiones de arquitectura con ADRs

- **Estado:** Aceptado
- **Fecha:** 2026-06-26
- **Decisores:** Equipo de plataforma

## Contexto

El proyecto creció de forma orgánica (flujo editorial multi-agente, RAG, UI)
sin un registro de las decisiones arquitectónicas. Esto dificulta el onboarding,
genera relitigio de decisiones ya tomadas y deja sin rastro el *porqué* de
cambios costosos de revertir (p. ej. autenticación, almacenamiento vectorial,
estado en memoria).

## Decisión

Adoptaremos **Architecture Decision Records** (formato Nygard) en
`docs/adr/`. Toda decisión arquitectónica significativa se documenta en un ADR
numerado, versionado en git y revisado vía PR.

## Alternativas consideradas

- **Wiki/Confluence externo** — se desincroniza del código y no entra en la
  revisión por PR.
- **Solo comentarios en el código** — no capturan contexto ni alternativas.
- **No documentar** — status quo; coste oculto en relitigio y onboarding.

## Consecuencias

- **Positivas:** trazabilidad del *porqué*, revisión junto al código, base para
  el modelo SDD ([ADR-0002](0002-adopt-spec-driven-development.md)).
- **Negativas / coste:** disciplina de mantener los ADRs al día.
- **Seguimiento:** plantilla en `docs/adr/0000-template.md`; los ADRs se
  enlazan desde las specs.
