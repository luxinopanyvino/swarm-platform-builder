---
description: Reconcilia las épicas/tareas del GitHub Project con la fuente de verdad SDD (docs/specs + docs/adr). Dry-run por defecto; pasa --apply para aplicar. Uso: /sdd-sync [--apply]
argument-hint: [--apply]
allowed-tools: Task, Bash(gh auth status:*)
---

Sincroniza el backlog (GitHub Project) con la fuente de verdad SDD.

Argumentos recibidos: **$ARGUMENTS**

1. Lanza el subagente **sdd-sync** (vía la tool Task). Reenvíale los argumentos tal
   cual: si `$ARGUMENTS` contiene `--apply`, el agente **aplica** los cambios; si
   no, ejecuta en **dry-run** (solo plan, sin mutar GitHub).
2. El agente lee `docs/specs/SPEC-*.md` (estado `Ready`/`In progress`/`Done`) y su
   bloque estructurado `sdd-sync`, contrasta con los issues `epic`/`task` actuales
   por su marcador oculto, y calcula el diff (crear/actualizar/drift).
3. Presenta su informe al usuario: CREATE / UPDATE / DRIFT / NO GESTIONADO y, en
   dry-run, recuérdale que debe volver a invocar con `--apply` para materializarlo.

Recuerda: el agente nunca cierra, borra ni reabre issues; solo reconcilia la
definición. El estado de ejecución se gestiona en GitHub.
