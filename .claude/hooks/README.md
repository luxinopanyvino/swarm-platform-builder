# Guardrails (hooks de Claude Code)

Guardarraíles que se ejecutan **dentro de las sesiones de Claude Code**, *antes*
de que una herramienta actúe. Complementan a la CI y la branch protection (el
gate duro para todos): esto detiene acciones contra la gobernanza de forma
temprana, durante el trabajo asistido.

> Ámbito: solo aplican a sesiones de Claude Code en este repo (vía
> `.claude/settings.json`). No sustituyen a la CI ni a la protección de ramas.

## `guard_git.py` — política de ramas (GOVERNANCE §3)

Hook `PreToolUse` sobre `Bash`. Bloquea (`permissionDecision: deny`):

- `git commit` o `git push` cuando la rama actual es **protegida**
  (`develop`/`main`/`master`). El trabajo va en ramas `feat|fix|sec|docs|chore/…`.
- `git push --force`/`-f` hacia una rama protegida.

Es **fail-open**: ante cualquier error o duda permite, para no estorbar (la CI +
branch protection son el control duro).

### Cómo probarlo

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git commit -m x"}}' \
  | python "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_git.py"
# En develop → imprime una decisión "deny"; en una rama feature → sin salida (allow).
```

## Nota cross-platform

El comando configurado en `settings.json` es
`python "$CLAUDE_PROJECT_DIR/.claude/hooks/guard_git.py"` (ruta absoluta vía
`$CLAUDE_PROJECT_DIR` para que resuelva desde la raíz sin importar el cwd).
En entornos donde el intérprete sea `python3` (p. ej. macOS sin alias `python`),
ajusta el comando del hook a `python3` en tu `.claude/settings.local.json`
(que tiene prioridad y no se versiona).
