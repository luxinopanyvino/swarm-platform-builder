#!/usr/bin/env python3
"""
Organiza el GitHub Project "Hardening & Platform Backlog" por épicas.

Crea un campo de selección única "Epic" (E1..E6) y asigna a cada issue su épica
correspondiente (las tareas T<n>.x -> E<n>; los [EPIC] por su título). Después,
en la UI del proyecto, activa  View -> Group by -> Epic  para ver las épicas con
sus tareas anidadas.

Requisitos: gh CLI autenticado con scope `project` (o GH_TOKEN con ese scope).
Uso:        python scripts/organize_project.py
"""
import json
import re
import subprocess
import sys

OWNER = "luxinopanyvino"
PROJECT_TITLE = "Hardening & Platform Backlog"
FIELD_NAME = "Epic"
EPICS = ["E1", "E2", "E3", "E4", "E5", "E6"]

# Mapeo de épicas por subcadena del título (ASCII-safe).
EPIC_BY_SUBSTR = [
    ("Identidad", "E1"),
    ("AppSec", "E2"),
    ("Infraestructura", "E3"),
    ("Datos y Persistencia", "E4"),
    ("Observabilidad", "E5"),
    ("Gobernanza", "E6"),
]


def gh(*args, capture=True):
    """Ejecuta gh y devuelve stdout (o lanza con el stderr si falla)."""
    res = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}\n{res.stderr.strip()}")
    return res.stdout


def gh_json(*args):
    return json.loads(gh(*args))


def epic_for_title(title: str):
    title = title or ""
    m = re.match(r"^T(\d)\.", title.strip())
    if m:
        return f"E{m.group(1)}"
    for substr, code in EPIC_BY_SUBSTR:
        if substr.lower() in title.lower():
            return code
    return None


def main():
    # 1. Localizar el proyecto por título
    projects = gh_json("project", "list", "--owner", OWNER, "--format", "json")["projects"]
    proj = next((p for p in projects if p.get("title") == PROJECT_TITLE), None)
    if not proj:
        sys.exit(f"No encuentro el proyecto '{PROJECT_TITLE}'. ¿GH_TOKEN con scope project?")
    number = str(proj["number"])
    project_id = proj["id"]
    print(f"Proyecto #{number} (id {project_id})")

    # 2. Crear el campo 'Epic' si no existe
    fields = gh_json("project", "field-list", number, "--owner", OWNER, "--format", "json")["fields"]
    field = next((f for f in fields if f.get("name") == FIELD_NAME), None)
    if not field:
        print(f"Creando campo '{FIELD_NAME}' (single-select)...")
        gh("project", "field-create", number, "--owner", OWNER,
           "--name", FIELD_NAME, "--data-type", "SINGLE_SELECT",
           "--single-select-options", ",".join(EPICS))
        fields = gh_json("project", "field-list", number, "--owner", OWNER, "--format", "json")["fields"]
        field = next((f for f in fields if f.get("name") == FIELD_NAME), None)
    field_id = field["id"]
    opt_by_name = {o["name"]: o["id"] for o in field.get("options", [])}
    print(f"Campo '{FIELD_NAME}' id {field_id}; opciones: {list(opt_by_name)}")

    # 3. Asignar cada item a su épica
    items = gh_json("project", "item-list", number, "--owner", OWNER,
                    "--format", "json", "--limit", "200")["items"]
    print(f"{len(items)} items en el proyecto")
    assigned, skipped = 0, 0
    for it in items:
        title = (it.get("content") or {}).get("title") or it.get("title") or ""
        code = epic_for_title(title)
        if not code or code not in opt_by_name:
            print(f"  - sin épica: {title[:60]}")
            skipped += 1
            continue
        gh("project", "item-edit", "--id", it["id"], "--project-id", project_id,
           "--field-id", field_id, "--single-select-option-id", opt_by_name[code])
        assigned += 1
    print(f"\nListo: {assigned} asignados, {skipped} sin épica.")
    print("Ahora en la UI del proyecto:  View ▸ Group by ▸ Epic")


if __name__ == "__main__":
    main()
