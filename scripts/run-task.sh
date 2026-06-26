#!/usr/bin/env bash
#
# Resuelve una o varias tareas del backlog por su número de issue, lanzando
# Claude Code en modo no interactivo con el comando /resolve-task.
#
# Uso:
#   bash scripts/run-task.sh 119
#   bash scripts/run-task.sh 119 120 121
#
# Requisitos: CLI `claude` instalada y `gh` autenticado (para leer los issues).
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Uso: bash scripts/run-task.sh <#issue> [<#issue> ...]" >&2
  exit 1
fi

command -v claude >/dev/null || { echo "ERROR: instala la CLI de Claude Code"; exit 1; }

# Acepta números con o sin '#'.
ISSUES=()
for a in "$@"; do ISSUES+=("${a#\#}"); done

echo "==> Resolviendo tarea(s): ${ISSUES[*]}"
claude -p "/resolve-task ${ISSUES[*]}"
