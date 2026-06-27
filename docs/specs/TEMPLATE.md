# SPEC-NNN: <título>

- **Estado:** Draft
- **Autor:** <nombre>
- **Fecha:** YYYY-MM-DD
- **Épica:** E<n> (GitHub Project)
- **ADR relacionado:** ADR-NNNN (si aplica)
- **Severidad:** 🔴 / 🟠 / 🟡 (si es remediación)

## 1. Problema

Qué falla hoy y por qué importa. Evidencia (archivo:línea, log, captura).

## 2. Objetivos / No-objetivos

- **Objetivos:** lo que esta spec debe lograr.
- **No-objetivos:** lo que queda fuera de alcance (para evitar scope creep).

## 3. Criterios de aceptación (Given/When/Then)

- [ ] **AC1** — *Given* … *When* … *Then* …
- [ ] **AC2** — …

Cada AC debe ser verificable por un test o comprobación.

## 4. Diseño propuesto

Enfoque técnico, archivos afectados, contratos de API, cambios de datos.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|

## 6. Plan de pruebas

Unitarias, integración, manual/seguridad. Cómo se valida cada AC.

## 7. Impacto operativo / observabilidad

Métricas, logs, migraciones, *rollout*/*rollback*.

## 8. Backlog (sincronización SDD)

Bloque **machine-readable** que el agente [`sdd-sync`](../../.claude/agents/sdd-sync.md)
lee para reconciliar la épica y las tareas de esta spec con el GitHub Project.
Es la **definición** (qué trabajo existe y sus criterios); el **estado de
ejecución** (open/closed, progreso) vive en GitHub y el agente no lo toca.

- Solo se sincroniza cuando el **Estado** de la spec es `Ready`, `In progress` o
  `Done` (las `Draft` no generan issues).
- Los `id` de épica (`E<n>`) y tarea (`T<n>.<m>`) son **estables**: no se
  reutilizan ni se renumeran. Renombrar el título es seguro; cambiar el `id` crea
  un issue nuevo.
- `depends_on` admite IDs de tarea (`T1.2`) o números de issue (`#34`).
- `acceptance` referencia los AC de la sección 3 (van al cuerpo del issue como DoD).

```yaml
# sdd-sync v1
epic:
  id: E0                       # E<n> — debe existir en el GitHub Project
  title: <título de la épica>
  area: area/<security|infra|backend|observability|governance>
tasks:
  - id: T0.1
    title: <título de la tarea>
    sev: high                  # high | medium | low
    depends_on: []             # [T0.0, "#34"] o []
    acceptance: [AC1, AC2]     # AC de la sección 3 que cubre esta tarea
  - id: T0.2
    title: <título de la tarea>
    sev: medium
    depends_on: [T0.1]
    acceptance: [AC3]
```
