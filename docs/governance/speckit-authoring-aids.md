# Capa de autoría Spec Kit (integrada al SDD)

Decisión: [ADR-0007](../adr/0007-adopt-spec-kit-authoring-layer.md). Este repo
mantiene su **propio** Spec-Driven Development (ver [GOVERNANCE.md](GOVERNANCE.md)):
la definición vive en `docs/specs/` + `docs/adr/`, el estado de ejecución en el
GitHub Project, y el flujo lo mueven `/sdd-sync`, `/resolve-task` y
`scripts/validate_specs.py`. **Eso no cambia.** Lo que Spec Kit aporta es la
**fase de autoría**: cómo nace y madura una spec antes de entrar a ese flujo.

## Mapeo Spec Kit → este repo

| Spec Kit | Aquí | Notas |
|---|---|---|
| *constitution* | `docs/governance/GOVERNANCE.md` | No se instala `.specify/` |
| `/speckit-specify` | **`/speckit-specify`** → `docs/specs/SPEC-NNN` desde [TEMPLATE](../specs/TEMPLATE.md) | Nace en `Draft` |
| `/speckit-clarify` | **`/speckit-clarify`** | ≤5 preguntas; graba `## Clarifications` en la spec |
| `/speckit-checklist` | **`/speckit-checklist`** | Escribe en `docs/specs/checklists/` |
| `/speckit-analyze` | **`/speckit-analyze`** | Cruza SPEC ↔ ADR ↔ bloque `sdd-sync`; solo lectura |
| `plan.md` | Sección 4 (*Diseño propuesto*) de la spec | No hay plan.md por feature |
| `tasks.md` | Bloque `sdd-sync` (sección 8) de la spec | `/sdd-sync` lo reconcilia con GitHub |
| `/speckit-implement` | `/resolve-task <#>` (agente `task-runner`) | Rama + tests + bitácora + PR |

## Pipeline de autoría (recomendado antes de `Ready`)

```
/speckit-specify "<necesidad>"          → SPEC-NNN en Draft
/speckit-clarify SPEC-NNN               → resolver ambigüedades (quedan en la spec)
/speckit-checklist SPEC-NNN <dominio>   → "unit tests for English" de los requisitos
/speckit-analyze SPEC-NNN               → consistencia SPEC ↔ ADR ↔ tareas
        │  (revisión de PR: Draft → Ready)
        ▼
/sdd-sync --apply                       → épica + tareas en el GitHub Project
/resolve-task <#>                       → implementación con DoD
```

Es el paso **recomendado** de la Definition of Ready (GOVERNANCE §5): una spec
no debería pasar a `Ready` sin al menos un pase de `clarify` y un `checklist`
del dominio dominante. Sigue siendo **no bloqueante en CI**: el gate duro es
`scripts/validate_specs.py` (esquema del bloque `sdd-sync`, IDs, áreas, AC).

`analyze` es el de **peor encaje** (Spec Kit lo diseñó para cruzar
`spec.md`+`plan.md`+`tasks.md` por feature): úsalo como chequeo blando, nunca
como sustituto del validador.

## Procedencia y actualización

Origen: [github/spec-kit](https://github.com/github/spec-kit), skills
`speckit-{specify,clarify,checklist,analyze}` copiadas a `.claude/skills/` y
adaptadas en sus puntos de integración (resolución del spec, rutas de salida,
referencia a GOVERNANCE, eliminación de los hooks `.specify/extensions.yml`).
Cada `SKILL.md` lleva una **"Nota de adaptación"** al inicio; si actualizas
desde upstream, re-aplica esas adaptaciones. No se adoptan `/speckit-plan`,
`/speckit-tasks` ni `/speckit-implement` (duplicarían sección 4, bloque
`sdd-sync` y `/resolve-task` — dos fuentes de verdad).
