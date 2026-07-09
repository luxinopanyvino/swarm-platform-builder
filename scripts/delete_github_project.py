#!/usr/bin/env python3
"""
Elimina lo creado por el seed: el/los Project(s) con el título dado y los issues
del backlog (labels `epic` y `task`).

DESTRUCTIVO. Requiere confirmación: ejecuta con  --yes  (o CONFIRM=yes).

Requisitos: gh CLI autenticado con scope `project` (o GH_TOKEN con ese scope).
Uso:        python scripts/delete_github_project.py --yes
"""
import json
import os
import subprocess
import sys

OWNER = "luxinopanyvino"
REPO = "luxinopanyvino/swarm-platform-builder"
PROJECT_TITLE = "Hardening & Platform Backlog"


def gh(*args, check=True):
    res = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if check and res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}\n{res.stderr.strip()}")
    return res.stdout, res.returncode


def gh_json(*args):
    out, _ = gh(*args)
    return json.loads(out)


def main():
    confirmed = "--yes" in sys.argv or os.environ.get("CONFIRM") == "yes"
    if not confirmed:
        sys.exit("DESTRUCTIVO. Reejecuta con --yes (o CONFIRM=yes) para borrar "
                 f"el Project '{PROJECT_TITLE}' y los issues con labels epic/task.")

    # 1. Borrar proyecto(s) que coincidan con el título
    projects = gh_json("project", "list", "--owner", OWNER, "--format", "json")["projects"]
    targets = [p for p in projects if p.get("title") == PROJECT_TITLE]
    if not targets:
        print(f"No hay proyectos con título '{PROJECT_TITLE}'.")
    for p in targets:
        gh("project", "delete", str(p["number"]), "--owner", OWNER)
        print(f"Project #{p['number']} eliminado")

    # 2. Borrar issues del backlog (labels epic y task)
    seen = set()
    for label in ("epic", "task"):
        issues = gh_json("issue", "list", "--repo", REPO, "--label", label,
                         "--state", "all", "--limit", "500", "--json", "number")
        for it in issues:
            n = it["number"]
            if n in seen:
                continue
            seen.add(n)
            gh("issue", "delete", str(n), "--repo", REPO, "--yes")
            print(f"Issue #{n} eliminado")

    print(f"\nHecho: {len(targets)} proyecto(s) y {len(seen)} issue(s) eliminados.")


if __name__ == "__main__":
    main()
