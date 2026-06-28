# Especificaciones (Spec-Driven Development)

Las **specs** describen el comportamiento esperado *antes* de implementarlo. Son
el contrato verificable entre producto, desarrollo y QA. Decisión:
[ADR-0002](../adr/0002-adopt-spec-driven-development.md).

## Ciclo de vida de una spec

```
Draft ──▶ Ready (cumple DoR) ──▶ In progress ──▶ Done (cumple criterios+DoD)
                                   └──▶ Superseded por SPEC-NNN (si cambia)
```

1. **Draft** — se crea desde `TEMPLATE.md` como `SPEC-NNN-titulo.md` en un PR.
2. **Ready** — revisada; cumple la *Definition of Ready*
   ([GOVERNANCE §5](../governance/GOVERNANCE.md)). Se desglosa en épica/tareas.
3. **In progress** — implementación en rama `feat/…` que referencia la spec.
4. **Done** — todos los **criterios de aceptación** verificados + *Definition of
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

## Índice

| Spec | Título | Estado | Épica |
|------|--------|--------|-------|
| [SPEC-001](SPEC-001-secure-registration-rbac.md) | Registro seguro y RBAC de mínimo privilegio | Ready | E1 |
| [SPEC-002](SPEC-002-scraper-ssrf-protection.md) | Protección SSRF del scraper del Investigador | Ready | E2 |
| [SPEC-003](SPEC-003-ux-design-system-accessibility.md) | Sistema de diseño y accesibilidad de la UI | Ready | E7 |
| [SPEC-013](SPEC-013-structural-refactor-project-independence.md) | Refactor estructural e independencia de proyectos | Draft | E8 |

> El resto de remediaciones están en
> [`docs/backlog/security-hardening-backlog.md`](../backlog/security-hardening-backlog.md);
> cada épica grande se promoverá a su propia spec antes de implementarse.
