#!/usr/bin/env python3
"""Guardrail PreToolUse para comandos git (hook de Claude Code).

Aplica la política de ramas de GOVERNANCE §3 *antes* de ejecutar el comando:
- Bloquea `git commit` / `git push` cuando la rama actual es protegida
  (develop/main/master): el trabajo va en ramas `feat|fix|sec|docs|chore/…`.
- Bloquea `git push --force` / `-f` hacia ramas protegidas.

Entrada: JSON del hook por stdin (tool_name, tool_input.command).
Salida: JSON con permissionDecision. "deny" detiene la herramienta con un motivo;
si no aplica, no emite decisión y el flujo de permisos sigue normal.

Diseñado para no estorbar: ante cualquier duda o error, permite (fail-open),
porque la CI + branch protection son el gate duro; esto es solo un aviso temprano.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

PROTECTED = {"develop", "main", "master"}


def _allow() -> None:
    # Sin decisión explícita: el flujo de permisos normal continúa.
    sys.exit(0)


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def _current_branch() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _allow()

    if data.get("tool_name") != "Bash":
        _allow()

    command = (data.get("tool_input") or {}).get("command", "") or ""

    # ¿El comando incluye un commit o un push de git?
    has_commit = bool(re.search(r"\bgit\b[^|&;]*\bcommit\b", command))
    has_push = bool(re.search(r"\bgit\b[^|&;]*\bpush\b", command))
    if not (has_commit or has_push):
        _allow()

    branch = _current_branch()

    # Force-push hacia una rama protegida (por flag o por rama actual).
    if has_push and re.search(r"\s(--force(-with-lease)?|-f)\b", command):
        if branch in PROTECTED or re.search(r"\b(develop|main|master)\b", command):
            _deny(
                "Force-push hacia una rama protegida bloqueado (GOVERNANCE §3). "
                "Si es imprescindible, ejecútalo tú manualmente fuera de la sesión."
            )

    # Commit o push estando en una rama protegida.
    if branch in PROTECTED:
        action = "commitear" if has_commit else "hacer push"
        _deny(
            f"No se permite {action} directamente en '{branch}' (GOVERNANCE §3: "
            f"prohibido el trabajo directo en ramas protegidas). Crea una rama "
            f"`feat|fix|sec|docs|chore/…` y abre una PR a develop."
        )

    _allow()


if __name__ == "__main__":
    main()
