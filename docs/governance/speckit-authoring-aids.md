# Ayudas de autoría Spec Kit (complemento opcional)

Este repo tiene su **propio** Spec-Driven Development (ver [GOVERNANCE.md](GOVERNANCE.md)):
la definición vive en `docs/specs/` + `docs/adr/`, el estado de ejecución en el
GitHub Project, y el flujo lo mueven `/sdd-sync`, `/resolve-task` y
`scripts/validate_specs.py`. **Eso no cambia.**

Sobre ese sistema hemos añadido **tres skills opcionales** tomadas de
[github/spec-kit](https://github.com/github/spec-kit) y **adaptadas** para operar
sobre nuestros artefactos (`docs/specs/SPEC-XXX`, `docs/adr/`, el bloque
`sdd-sync`) en lugar del andamiaje `specs/NNN/spec.md` + `.specify/` de Spec Kit.
Son **ayudas de autoría de la spec**, no un reemplazo del flujo ni del backlog.

> No se instala `.specify/` ni el resto de comandos de Spec Kit
> (`/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`, …).
> La "constitution" de Spec Kit se mapea a **`docs/governance/GOVERNANCE.md`**.

## Los tres skills

| Skill | Para qué | Entrada | Salida |
|-------|----------|---------|--------|
| **`/speckit-clarify`** | Detecta ambigüedades del SPEC y hace ≤5 preguntas dirigidas, grabando las respuestas en el propio spec | `SPEC-XXX` (o ruta) + áreas opcionales | Edita el SPEC (sección `## Clarifications`) |
| **`/speckit-checklist`** | Genera un checklist de **calidad de requisitos** ("unit tests for English") para un dominio (seguridad, UX, API…) | `SPEC-XXX` + dominio | `docs/specs/checklists/<SPEC-id>-<dominio>.md` |
| **`/speckit-analyze`** | Análisis **solo lectura** de consistencia entre SPEC ↔ ADR ↔ bloque `sdd-sync` | `SPEC-XXX` | Informe en pantalla (no escribe) |

`analyze` es el de **peor encaje**: Spec Kit lo diseñó para cruzar
`spec.md`+`plan.md`+`tasks.md` (que aquí no existen por-feature), así que se
reinterpreta contra nuestros artefactos. Úsalo como chequeo blando, no como gate:
el gate real sigue siendo `scripts/validate_specs.py` en CI.

## Cuándo usarlas

Al preparar un SPEC **antes** de pasarlo a *Ready* / antes de `/resolve-task`:

1. `/speckit-clarify SPEC-XXX` — resolver ambigüedades.
2. `/speckit-checklist SPEC-XXX seguridad` — validar completitud de requisitos.
3. `/speckit-analyze SPEC-XXX` — consistencia SPEC↔ADR↔tareas.

Todas son opcionales y no forman parte de la Definition of Done.

## Procedencia y actualización

Origen: `github/spec-kit` (skills `speckit-{clarify,checklist,analyze}`). Se
copiaron y se editaron los puntos de integración (resolución del spec, rutas de
salida, referencia a GOVERNANCE, eliminación de los hooks `.specify/extensions.yml`).
Si actualizas desde upstream, re-aplica esas adaptaciones (marcadas con la "Nota
de adaptación" al inicio de cada `SKILL.md`).
