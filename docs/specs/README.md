# Especificaciones (Spec-Driven Development)

Las **specs** describen el comportamiento esperado *antes* de implementarlo. Son
el contrato verificable entre producto, desarrollo y QA. Decisiones:
[ADR-0002](../adr/0002-adopt-spec-driven-development.md) (SDD) y
[ADR-0007](../adr/0007-adopt-spec-kit-authoring-layer.md) (capa de autoría
Spec Kit).

## Ciclo de vida de una spec

```
/speckit-specify ──▶ Draft ──▶ Ready (cumple DoR) ──▶ In progress ──▶ Done
      autoría:        │ /speckit-clarify · /speckit-checklist · /speckit-analyze
                      └──▶ Superseded por SPEC-NNN (si cambia o desaparece el problema)
```

1. **Draft** — se crea con `/speckit-specify` (o a mano desde `TEMPLATE.md`)
   como `SPEC-NNN-titulo.md` en un PR.
2. **Autoría** — antes de Ready se recomienda el pipeline Spec Kit:
   `/speckit-clarify` (ambigüedades), `/speckit-checklist <dominio>` (calidad de
   requisitos) y `/speckit-analyze` (consistencia SPEC↔ADR↔tareas). Ver
   [speckit-authoring-aids.md](../governance/speckit-authoring-aids.md).
3. **Ready** — revisada; cumple la *Definition of Ready*
   ([GOVERNANCE §5](../governance/GOVERNANCE.md)). `/sdd-sync --apply` siembra
   su épica/tareas en el GitHub Project.
4. **In progress** — implementación vía `/resolve-task <#>` en ramas con prefijo.
5. **Done** — todos los **criterios de aceptación** verificados + *Definition of
   Done*.

## Convenciones

- ID incremental `SPEC-NNN`. No se reutiliza ni se borra.
- Criterios de aceptación en formato **Given/When/Then** y verificables (un test
  o comprobación los puede validar).
- Las specs enlazan a su ADR (si lo hay) y a su épica del backlog.
- Cambios de comportamiento → nueva versión o `Superseded`.
- La **épica y tareas** de la spec se declaran en el bloque estructurado
  `sdd-sync` (sección 8 del [TEMPLATE](TEMPLATE.md)). El agente
  [`sdd-sync`](../../.claude/agents/sdd-sync.md) (comando `/sdd-sync`) reconcilia
  ese bloque con el GitHub Project sin tocar el estado de ejecución. Ver
  [GOVERNANCE §7](../governance/GOVERNANCE.md).
- Los `id` de tarea (`T<n>.<m>`) son **globales**: dos specs pueden alimentar la
  misma épica (p. ej. SPEC-001 y SPEC-015 → E1), pero un `T-id` solo puede
  declararse en una spec. Gate en CI: `scripts/validate_specs.py`.

## Índice

| Spec | Título | Estado | Épica |
|------|--------|--------|-------|
| [SPEC-001](SPEC-001-secure-registration-rbac.md) | Registro seguro y RBAC de mínimo privilegio | Ready | E1 |
| [SPEC-002](SPEC-002-scraper-ssrf-protection.md) | Protección SSRF del scraper del Investigador | Superseded | E2 |
| [SPEC-003](SPEC-003-ux-design-system-accessibility.md) | Sistema de diseño y accesibilidad de la UI | Ready | E7 |
| [SPEC-013](SPEC-013-structural-refactor-project-independence.md) | Refactor estructural e independencia de proyectos | Ready | E8 |
| [SPEC-014](SPEC-014-explainability-and-edd.md) | Explicabilidad del pipeline y Evaluation-Driven Development (EDD) | Ready | E9 |
| [SPEC-015](SPEC-015-identity-session-hardening.md) | Endurecimiento de identidad y sesiones (E1 resto) | In progress | E1 |
| [SPEC-016](SPEC-016-appsec-output-upload-errors.md) | AppSec: saneamiento de salida, subidas y errores (E2 resto) | Ready | E2 |
| [SPEC-017](SPEC-017-infra-deploy-hardening.md) | Infraestructura y despliegue endurecidos | In progress | E3 |
| [SPEC-018](SPEC-018-data-persistence.md) | Datos y persistencia gestionados | Ready | E4 |
| [SPEC-019](SPEC-019-observability.md) | Observabilidad del backend y del pipeline | Ready | E5 |
| [SPEC-020](SPEC-020-governance-supply-chain.md) | Gobernanza, CI y cadena de suministro | In progress | E6 |
| [SPEC-021](SPEC-021-agent-memory-context-budget.md) | Memoria a largo plazo y presupuesto de contexto de los agentes | Draft | E10 |

> Con SPEC-015…020 **todas las épicas del backlog (E1–E9) están respaldadas por
> una spec**: las tareas sembradas por el bootstrap
> (`scripts/seed_github_project.py`) quedaron adoptadas retroactivamente y
> `/sdd-sync --apply` las reconcilia (ADOPT) sin tocar su estado.
> [`docs/backlog/security-hardening-backlog.md`](../backlog/security-hardening-backlog.md)
> queda como overview humano de alto nivel.
