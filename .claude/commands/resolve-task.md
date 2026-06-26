---
description: Implementa una o varias tareas del backlog por su número de issue de GitHub. Uso: /resolve-task 119 [120 ...]
argument-hint: <#issue> [<#issue> ...]
allowed-tools: Bash(gh issue view:*), Bash(gh issue list:*), Task
---

Resuelve la(s) tarea(s) del backlog cuyos números de issue son: **$ARGUMENTS**

Para **cada** número de issue indicado, en orden:

1. Lee la tarea para tener el contexto a la vista:
   `gh issue view <N> --repo luxinopanyvino/swarm-platform-builder --json number,title,body,labels,state`
2. Si el issue no es una tarea (`label: task`) o ya está cerrado, indícalo y pasa
   al siguiente.
3. Lanza el subagente **task-runner** (vía la tool Task) para implementarla de
   extremo a extremo: debe leer su Definition of Done y sus dependencias
   ("Bloqueada por: #X"), verificar que las dependencias estén cerradas, crear una
   rama, implementar, ejecutar las pruebas y reportar el cumplimiento del DoD.
4. Si una tarea está bloqueada por una dependencia abierta, **no** la implementes:
   anótalo y continúa con las demás.

Al terminar, presenta un resumen por tarea: estado (resuelta / bloqueada /
omitida), rama creada y verificación ejecutada. No hagas `git push` ni cierres
issues salvo que el usuario lo pida explícitamente.
