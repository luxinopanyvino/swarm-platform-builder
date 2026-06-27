#!/usr/bin/env python3
"""Guardrail PreToolUse para comandos git (hook de Claude Code).

Aplica políticas de GOVERNANCE §3 y de higiene de seguridad *antes* de ejecutar:

- DENY: `git commit`/`git push` en rama protegida (develop/main/master).
- DENY: `git push --force`/`-f` hacia una rama protegida.
- DENY: `--no-verify` en commit/push (saltarse hooks/CI no está permitido).
- DENY: `git add -f`/`--force` de archivos sensibles ignorados
  (settings.local.json, .env, *.db, claves) — evita re-introducir secretos.
- ASK:  operaciones destructivas de historial/árbol (`git reset --hard`,
  `git clean -fd…`) — requieren confirmación explícita del usuario.

Entrada: JSON del hook por stdin (tool_name, tool_input.command).
Salida: JSON con permissionDecision (deny/ask). Si no aplica, sin salida (allow).
Fail-open: ante error o duda, permite (la CI + branch protection son el gate duro).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

PROTECTED = {"develop", "main", "master"}

# Archivos que nunca deben forzarse al índice (secretos / datos locales).
SENSITIVE = re.compile(
    r"(settings\.local\.json|\.env(\.[\w.-]+)?\b|\.db\b|\.pem\b|\.key\b|id_rsa)",
    re.IGNORECASE,
)


def _emit(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def _allow() -> None:
    sys.exit(0)


def _sanitize(cmd: str) -> str:
    """Quita cuerpos de heredoc y literales entrecomillados.

    Así los chequeos de flags no se disparan por el *contenido* de un mensaje de
    commit (p. ej. `-m "... --no-verify ..."`), solo por flags reales del comando.
    """
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[\s\S]*?\n\1\b", " ", cmd)  # heredocs
    cmd = re.sub(r"'[^']*'", " ", cmd)   # '...'
    cmd = re.sub(r'"[^"]*"', " ", cmd)   # "..."
    return cmd


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

    raw = (data.get("tool_input") or {}).get("command", "") or ""
    # Analizar sobre la versión saneada: ignora mensajes/heredocs entrecomillados.
    cmd = _sanitize(raw)
    if not re.search(r"\bgit\b", cmd):
        _allow()

    has_commit = bool(re.search(r"\bgit\b[^|&;]*\bcommit\b", cmd))
    has_push = bool(re.search(r"\bgit\b[^|&;]*\bpush\b", cmd))
    has_add = bool(re.search(r"\bgit\b[^|&;]*\badd\b", cmd))

    # 1) Saltarse las verificaciones (hooks/CI) no está permitido.
    if (has_commit or has_push) and re.search(r"\s--no-verify\b", cmd):
        _emit("deny",
              "No uses --no-verify: salta las verificaciones de commit/push. "
              "Corrige la causa en lugar de evitar el control.")

    # 2) Force-add de archivos sensibles ignorados.
    if has_add and re.search(r"\b(add)\b[^|&;]*\s(-f|--force)\b", cmd) and SENSITIVE.search(cmd):
        _emit("deny",
              "Bloqueado `git add --force` de un archivo sensible (secreto/datos "
              "locales). Esos archivos están ignorados a propósito; no los versiones.")

    branch = _current_branch()

    # 3) Force-push hacia rama protegida.
    if has_push and re.search(r"\s(--force(-with-lease)?|-f)\b", cmd):
        if branch in PROTECTED or re.search(r"\b(develop|main|master)\b", cmd):
            _emit("deny",
                  "Force-push hacia una rama protegida bloqueado (GOVERNANCE §3). "
                  "Si es imprescindible, hazlo tú manualmente fuera de la sesión.")

    # 4) Commit/push directo en rama protegida.
    if branch in PROTECTED and (has_commit or has_push):
        action = "commitear" if has_commit else "hacer push"
        _emit("deny",
              f"No se permite {action} directamente en '{branch}' (GOVERNANCE §3). "
              f"Crea una rama `feat|fix|sec|docs|chore/…` y abre una PR a develop.")

    # 5) Operaciones destructivas → pedir confirmación.
    if re.search(r"\bgit\b[^|&;]*\breset\b[^|&;]*\s--hard\b", cmd):
        _emit("ask",
              "`git reset --hard` descarta cambios de forma irreversible. "
              "Confirma que es lo que quieres.")
    if re.search(r"\bgit\b[^|&;]*\bclean\b[^|&;]*\s-[a-z]*f[a-z]*d|\bgit\b[^|&;]*\bclean\b[^|&;]*\s-[a-z]*d[a-z]*f", cmd):
        _emit("ask",
              "`git clean -fd…` borra archivos no rastreados de forma irreversible. "
              "Confirma antes de continuar.")

    _allow()


if __name__ == "__main__":
    main()
