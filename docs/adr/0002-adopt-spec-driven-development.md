# ADR-0002: Adoptar Spec-Driven Development (SDD)

- **Estado:** Aceptado
- **Fecha:** 2026-06-26
- **Decisores:** Equipo de plataforma
- **Specs relacionadas:** todas (ver `docs/specs`)

## Contexto

El desarrollo reciente ha sido reactivo: cambios encadenados a partir de
feedback puntual, sin criterios de aceptación explícitos ni una definición
previa del comportamiento esperado. Esto produjo:

- features con bugs detectados tarde (referencias mal formateadas, extracción de
  metadatos poco fiable, guardado de agente roto por slug/UUID),
- ausencia de criterios objetivos de "terminado",
- difícil priorización frente a la deuda (ver auditoría de seguridad).

Queremos un método ligero que ponga la **especificación antes que el código**.

## Decisión

Adoptaremos **Spec-Driven Development (SDD)**:

1. Toda épica/feature significativa comienza con una **spec** en `docs/specs/`
   (plantilla en `docs/specs/TEMPLATE.md`) con: problema, objetivos, criterios
   de aceptación verificables, diseño, riesgos y plan de pruebas.
2. La spec pasa por **Definition of Ready (DoR)** antes de implementarse.
3. La implementación referencia la spec; el PR no se mergea hasta cumplir los
   **criterios de aceptación** y la **Definition of Done (DoD)**.
4. Las decisiones arquitectónicas dentro de una spec se elevan a **ADR**.
5. El flujo es: `Spec → ADR (si aplica) → Épica/Tareas → Implementación → PR →
   Verificación contra criterios`.

## Alternativas consideradas

- **Solo issues de GitHub** — pierden el "porqué" y los criterios estructurados.
- **Documentación pesada (waterfall)** — demasiado coste; queremos specs vivas y
  ligeras, no contratos cerrados.
- **TDD puro sin specs** — los tests no capturan el contexto de producto ni los
  requisitos no funcionales (seguridad, observabilidad).

## Consecuencias

- **Positivas:** criterios objetivos de aceptación, mejor priorización, menos
  retrabajo, trazabilidad spec → PR → release.
- **Negativas / coste:** trabajo previo de redacción; requiere disciplina en DoR/DoD.
- **Seguimiento:** `docs/specs/README.md` define el ciclo de vida; `CONTRIBUTING.md`
  integra SDD en el flujo de PRs; CODEOWNERS exige revisión.
