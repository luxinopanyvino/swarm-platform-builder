#!/usr/bin/env python3
"""Guardrail PreToolUse contra borrados destructivos de ficheros (hook Bash).

- DENY: `rm -rf` sobre objetivos catastróficos (`/`, `~`, `$HOME`, `/*`, `~/*`).
- ASK:  `rm -rf` sobre rutas absolutas o de home (fuera del repo) — confirma.
- ALLOW: borrados relativos (scratch, build, dentro del proyecto).

Fail-open: ante error o duda, permite. Complementa a la CI/branch protection.
"""
from __future__ import annotations

import json
import re
import shlex
import sys

CATASTROPHIC = {"/", "~", "~/", "$HOME", "/*", "~/*", "$HOME/*", "."}


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
    """Quita heredocs y literales entrecomillados para no analizar el contenido
    de mensajes (p. ej. un commit que *menciona* `rm -rf /`)."""
    cmd = re.sub(r"<<-?\s*['\"]?(\w+)['\"]?[\s\S]*?\n\1\b", " ", cmd)
    cmd = re.sub(r"'[^']*'", " ", cmd)
    cmd = re.sub(r'"[^"]*"', " ", cmd)
    return cmd


def _is_absolute_or_home(target: str) -> bool:
    return (
        target.startswith("/")
        or target.startswith("~")
        or target.startswith("$HOME")
        or bool(re.match(r"^[A-Za-z]:[\\/]", target))  # C:\ en Windows
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        _allow()

    if data.get("tool_name") != "Bash":
        _allow()

    raw = (data.get("tool_input") or {}).get("command", "") or ""
    cmd = _sanitize(raw)

    # ¿Hay un `rm` recursivo+forzado? (-rf, -fr, -r -f, --recursive --force, …)
    if not re.search(r"\brm\b", cmd):
        _allow()
    recursive = bool(re.search(r"-[a-z]*r", cmd) or "--recursive" in cmd)
    forced = bool(re.search(r"-[a-z]*f", cmd) or "--force" in cmd)
    if not (recursive and forced):
        _allow()

    # Extraer objetivos (lo que no es flag).
    try:
        tokens = shlex.split(cmd, posix=True)
    except ValueError:
        _allow()
    targets = [t for t in tokens[1:] if not t.startswith("-") and t != "rm"]

    for t in targets:
        if t in CATASTROPHIC or re.match(r"^/\w*\*?$", t):
            _emit("deny",
                  f"Borrado catastrófico bloqueado: `rm -rf {t}`. "
                  f"Si de verdad lo necesitas, ejecútalo tú manualmente.")

    for t in targets:
        if _is_absolute_or_home(t):
            _emit("ask",
                  f"`rm -rf` sobre una ruta fuera del proyecto (`{t}`). "
                  f"Confirma que es correcto.")

    _allow()


if __name__ == "__main__":
    main()
