# Bitácora de tareas

Registro cronológico de las tareas del backlog resueltas por el agente
`task-runner` (o manualmente siguiendo el mismo formato).

## Convención

- **Un archivo por tarea**, nombrado `tarea-<N>.md` donde `<N>` es el número de
  issue de GitHub (p. ej. `tarea-119.md`).
- Cada ejecución **exitosa** añade una entrada datada al archivo de su tarea. Si
  una tarea se retoma o re-ejecuta, se **añade** una nueva entrada (no se borra la
  anterior), preservando la traza completa.
- La bitácora se versiona junto al código en la misma rama/PR de la tarea, de modo
  que el registro viaja con el cambio que documenta.

## Plantilla de entrada

```markdown
# Tarea #<N> — <título de la tarea>

## <YYYY-MM-DD HH:MM> — Completada ✅

- **Rama:** `<tipo>/<id>-<slug>`
- **PR:** #<num> → `develop`
- **Spec/ADR:** <referencias o "—">
- **Dependencias:** <#X resueltas o "ninguna">

### Qué se hizo
<resumen breve del cambio>

### Definition of Done
- [x] <criterio 1> — <cómo se cumple>
- [x] <criterio 2> — <cómo se cumple>

### Verificación
- <comando ejecutado> → <resultado>

### Fuera de alcance / notas
<lo que se dejó fuera, riesgos o seguimiento>
```
