---
name: "speckit-specify"
description: "Crea una nueva spec SDD (docs/specs/SPEC-NNN) desde TEMPLATE.md a partir de una descripción de funcionalidad, con bloque sdd-sync listo para reconciliar."
argument-hint: "Descripción de la funcionalidad/necesidad + (opcional) épica E<n> destino"
compatibility: "Adaptado a este repo: escribe docs/specs/SPEC-NNN desde TEMPLATE.md; NO usa el andamiaje .specify/ de Spec Kit"
metadata:
  author: "github-spec-kit (adaptado para swarm-platform-builder)"
  source: "templates/commands/specify.md"
user-invocable: true
disable-model-invocation: false
---

> **Nota de adaptación.** Skill de autoría tomada de
> [github/spec-kit](https://github.com/github/spec-kit) y adaptada al SDD de este
> repo (ADR-0007): en lugar de crear `specs/NNN/spec.md` + rama por feature,
> escribe `docs/specs/SPEC-NNN-<slug>.md` desde
> [`TEMPLATE.md`](../../../docs/specs/TEMPLATE.md). La "constitution" es
> **`docs/governance/GOVERNANCE.md`**. El equivalente de `plan.md` es la sección 4
> del spec y el de `tasks.md` es el bloque `sdd-sync` (sección 8).

Crea una **nueva especificación SDD** a partir de la descripción recibida en
`$ARGUMENTS`.

## Pasos

1. **Numera**: lista `docs/specs/SPEC-*.md` y toma el siguiente `NNN` libre
   (incremental; los IDs nunca se reutilizan ni renumeran).
2. **Contexto**: lee `docs/governance/GOVERNANCE.md` (§5 DoR, §7 áreas
   registradas), `docs/specs/README.md` (ciclo de vida) y los ADR relacionados
   con el dominio de la petición. Si la descripción menciona una épica `E<n>`
   existente, revisa qué specs ya declaran tareas en ella (los `T<n>.<m>` son
   globales y no pueden colisionar: usa el siguiente `m` libre de esa épica).
3. **Redacta** `docs/specs/SPEC-NNN-<slug>.md` siguiendo `TEMPLATE.md` completo:
   - **Estado: Draft** (nunca nace Ready; Ready lo decide la revisión del PR).
   - Problema con evidencia (`archivo:línea` cuando exista).
   - Objetivos / No-objetivos (contén el *scope creep* desde el principio).
   - **AC en Given/When/Then verificables** — cada AC debe poder validarlo un
     test o comprobación; sin adverbios vagos ("rápido", "seguro") sin métrica.
   - Bloque `sdd-sync` (sección 8) con `epic{id,title,area}` y `tasks[]` cuyos
     `acceptance` referencian los AC de la sección 3. `area` debe estar en las
     **áreas registradas** de GOVERNANCE §7.
4. **Autovalida**: ejecuta `python scripts/validate_specs.py` y corrige hasta
   que pase (las Draft sin bloque están permitidas, pero si incluyes bloque debe
   ser válido).
5. **Siguiente paso sugerido** (pipeline de autoría, ADR-0007): indica al usuario
   que antes de pasar la spec a `Ready` conviene `/speckit-clarify SPEC-NNN`,
   `/speckit-checklist SPEC-NNN <dominio>` y `/speckit-analyze SPEC-NNN`; y que
   tras el merge en `Ready`, `/sdd-sync --apply` siembra épica/tareas en el
   GitHub Project.

## Reglas

- Marca toda ambigüedad que no puedas resolver con `[NEEDS CLARIFICATION: …]`
  en el propio spec (es el input de `/speckit-clarify`); no inventes requisitos.
- No toques specs existentes ni el backlog: esta skill **solo añade** un fichero
  nuevo bajo `docs/specs/`.
- No abras PR ni hagas commit salvo que el usuario lo pida explícitamente.
