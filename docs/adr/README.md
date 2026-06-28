# Architecture Decision Records (ADR)

Este directorio contiene los **Architecture Decision Records** del proyecto
swarm-platform-builder / AlejandrIA Magazine. Un ADR captura una decisión
arquitectónica significativa, su contexto y sus consecuencias.

## ¿Cuándo escribir un ADR?

Crea un ADR cuando una decisión:
- afecta a la estructura, dependencias, interfaces o cualidades del sistema
  (seguridad, rendimiento, operabilidad), o
- es costosa de revertir, o
- genera debate o requiere alineación entre varias personas.

## Proceso

1. Copia `0000-template.md` a `NNNN-titulo-en-kebab-case.md` (NNNN incremental).
2. Estado inicial: `Propuesto`. Ábrelo en un PR.
3. Se discute en la revisión; al aprobarse pasa a `Aceptado`.
4. Si una decisión posterior lo invalida, marca el ADR antiguo como
   `Reemplazado por ADR-NNNN` (no se borra: el historial es valioso).

## Estados

`Propuesto` · `Aceptado` · `Rechazado` · `Obsoleto` · `Reemplazado por ADR-NNNN`

## Índice

| ADR | Título | Estado |
|-----|--------|--------|
| [0001](0001-record-architecture-decisions.md) | Registrar decisiones de arquitectura con ADRs | Aceptado |
| [0002](0002-adopt-spec-driven-development.md) | Adoptar Spec-Driven Development (SDD) | Aceptado |
| [0003](0003-security-baseline-and-threat-model.md) | Línea base de seguridad y modelo de amenazas | Propuesto |
| [0004](0004-observability-and-ci.md) | Observabilidad mínima y CI/CD con escaneo de cadena de suministro | Propuesto |
| [0005](0005-nocode-architecture.md) | Arquitectura no-code: motor vs paquetes de proyecto e independencia de proyectos | Propuesto |

Ver también: [docs/specs](../specs) (especificaciones SDD) y
[docs/governance](../governance) (gobernanza, DoD, CODEOWNERS).
