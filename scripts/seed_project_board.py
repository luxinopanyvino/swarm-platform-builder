#!/usr/bin/env python3
"""Coloca en el tablero del Project los issues que las specs declaran.

**Qué NO hace, y es lo importante:** no crea, no cierra, no edita ni borra issues.
De eso se encarga `/sdd-sync`, que reconcilia la *definición*. Este script solo
resuelve el último tramo —que los issues que ya existen estén **en el tablero**—,
que es un paso aparte porque Projects v2 vive en GraphQL y no en la API REST donde
viven los issues.

Por qué no vale `seed_github_project.py`: aquel es un **bootstrap de un solo uso**
con las épicas escritas a mano en el propio fichero (E1–E6, 28 tareas). No lee las
specs, así que no conoce ninguna épica posterior, y sobre un Project existente solo
corre con `--force`, que lo recrea de forma destructiva. Este script es lo
contrario: lee las specs, es incremental y no destruye nada.

**Dry-run por defecto**, como `/sdd-sync`: sin `--apply` enseña el plan y no toca
nada.

Requisitos: `gh` autenticado con scope `project` (`gh auth refresh -s project`).
No funciona desde una sesión de Claude Code: GraphQL está bloqueado ahí y Projects
v2 solo habla GraphQL.

Uso:
    python scripts/seed_project_board.py                      # plan
    python scripts/seed_project_board.py --apply              # aplicar
    python scripts/seed_project_board.py --project "Otro"     # otro tablero

El campo single-select «Epic» queda **fuera de alcance** a propósito: darle valor a
una épica nueva exige crear antes su opción, y eso es un cambio de esquema del
Project que merece una persona delante.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

RAIZ = Path(__file__).resolve().parents[1]
SPECS_DIR = RAIZ / "docs" / "specs"

#: Mismos estados que `validate_specs.py`: una spec en `Draft` no genera issues, así
#: que tampoco tiene nada que colocar en el tablero.
ESTADOS_SINCRONIZABLES = {"Ready", "In progress", "Done"}

OWNER_POR_DEFECTO = "luxinopanyvino"
REPO_POR_DEFECTO = "luxinopanyvino/swarm-platform-builder"
TABLERO_POR_DEFECTO = "Hardening & Platform Backlog"

_ESTADO_RE = re.compile(r"^\s*-\s*\*\*Estado:\*\*\s*(.+?)\s*$", re.MULTILINE)
_MARCADOR_RE = re.compile(r"<!--\s*sdd:(epic|task):([A-Za-z0-9.]+)\s*-->")


# ── Lectura de las specs (puro: sin red, sin gh) ─────────────────────────────

@dataclass(frozen=True)
class Definicion:
    """Lo que las specs dicen que debe existir, por marcador."""

    marcadores: Dict[str, str]  # "epic:E14" -> título declarado
    ignoradas: Tuple[Tuple[str, str], ...] = ()  # (spec, estado) que no sincronizan

    def __len__(self) -> int:
        return len(self.marcadores)


def _bloque_sync(texto: str) -> Optional[dict]:
    for m in re.finditer(r"```ya?ml\s*\n(.*?)```", texto, re.DOTALL):
        cuerpo = m.group(1)
        if cuerpo.splitlines() and "sdd-sync" in cuerpo.splitlines()[0]:
            return yaml.safe_load(cuerpo)
    return None


def leer_definicion(specs_dir: Path = SPECS_DIR) -> Definicion:
    """Marcadores que las specs sincronizables declaran.

    Una épica puede declararla más de una spec —aquí es legítimo: E2 la comparten
    SPEC-002 (Superseded), SPEC-016 y SPEC-024—, así que el marcador se queda con
    el primer título que lo declare y no se duplica la entrada.
    """
    marcadores: Dict[str, str] = {}
    ignoradas: List[Tuple[str, str]] = []

    for ruta in sorted(specs_dir.glob("SPEC-*.md")):
        texto = ruta.read_text(encoding="utf-8")
        estado = _ESTADO_RE.search(texto)
        estado = estado.group(1).strip() if estado else "(sin estado)"
        if estado not in ESTADOS_SINCRONIZABLES:
            ignoradas.append((ruta.name, estado))
            continue
        datos = _bloque_sync(texto)
        if not datos:
            continue
        epica = datos.get("epic") or {}
        if epica.get("id"):
            marcadores.setdefault(f"epic:{epica['id']}", str(epica.get("title", "")))
        for tarea in datos.get("tasks") or []:
            if tarea.get("id"):
                marcadores.setdefault(f"task:{tarea['id']}", str(tarea.get("title", "")))

    return Definicion(marcadores=marcadores, ignoradas=tuple(ignoradas))


def marcador_de(cuerpo: Optional[str]) -> Optional[str]:
    """`<!-- sdd:task:T14.1 -->` → `task:T14.1`. `None` si el issue no lo lleva."""
    if not cuerpo:
        return None
    m = _MARCADOR_RE.search(cuerpo)
    return f"{m.group(1)}:{m.group(2)}" if m else None


def indexar_issues(issues: Iterable[dict]) -> Dict[str, dict]:
    """Marcador → issue. Los issues sin marcador no los gestiona el SDD."""
    indice: Dict[str, dict] = {}
    for issue in issues:
        marca = marcador_de(issue.get("body"))
        if marca:
            indice.setdefault(marca, issue)
    return indice


# ── El plan (puro) ───────────────────────────────────────────────────────────

@dataclass
class Plan:
    #: Issues que hay que añadir al tablero: (marcador, número, url).
    anadir: List[Tuple[str, int, str]] = field(default_factory=list)
    #: Ya estaban: no se tocan.
    presentes: List[str] = field(default_factory=list)
    #: Las specs los declaran y no existe issue: es trabajo de `/sdd-sync`.
    sin_issue: List[str] = field(default_factory=list)

    @property
    def hay_trabajo(self) -> bool:
        return bool(self.anadir)


def planificar(
    definicion: Definicion,
    indice: Dict[str, dict],
    urls_en_tablero: Iterable[str],
) -> Plan:
    """Qué falta por colocar. No decide borrar nada: el tablero puede tener items
    legítimos que no vengan del SDD, y este script no es quién para juzgarlos."""
    ya = set(urls_en_tablero)
    plan = Plan()
    for marca in sorted(definicion.marcadores):
        issue = indice.get(marca)
        if issue is None:
            plan.sin_issue.append(marca)
            continue
        url = issue.get("html_url") or issue.get("url") or ""
        if url in ya:
            plan.presentes.append(marca)
        else:
            plan.anadir.append((marca, int(issue["number"]), url))
    return plan


# ── Borde con `gh` (lo único que toca la red) ────────────────────────────────

class GhNoDisponible(RuntimeError):
    pass


def gh(*args: str) -> str:
    try:
        res = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError as error:
        raise GhNoDisponible(
            "`gh` no está instalado. Projects v2 solo habla GraphQL y este script lo "
            "usa a través de gh; instálalo y autentícalo con `gh auth refresh -s project`."
        ) from error
    if res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}\n{res.stderr.strip()}")
    return res.stdout


def gh_json(*args: str):
    return json.loads(gh(*args) or "null")


def numero_de_tablero(owner: str, titulo: str) -> int:
    datos = gh_json("project", "list", "--owner", owner, "--format", "json", "--limit", "100")
    for proyecto in (datos or {}).get("projects", []):
        if proyecto.get("title") == titulo:
            return int(proyecto["number"])
    disponibles = ", ".join(repr(p.get("title")) for p in (datos or {}).get("projects", []))
    raise RuntimeError(f"No hay ningún Project titulado {titulo!r}. Hay: {disponibles or '(ninguno)'}")


def issues_gestionables(repo: str) -> List[dict]:
    """Issues con label `epic` o `task`, abiertos o cerrados.

    Cerrados incluidos a propósito: una épica terminada sigue perteneciendo al
    tablero, y dejarla fuera daría un tablero que no cuenta la historia completa.
    """
    salida: List[dict] = []
    for etiqueta in ("epic", "task"):
        salida.extend(gh_json(
            "api", "--paginate",
            f"repos/{repo}/issues?state=all&labels={etiqueta}&per_page=100",
        ) or [])
    # Un issue puede llevar las dos labels; se deduplica por número.
    unicos = {int(i["number"]): i for i in salida if "pull_request" not in i}
    return list(unicos.values())


def urls_del_tablero(owner: str, numero: int) -> List[str]:
    datos = gh_json("project", "item-list", str(numero), "--owner", owner,
                    "--format", "json", "--limit", "1000")
    urls = []
    for item in (datos or {}).get("items", []):
        contenido = item.get("content") or {}
        url = contenido.get("url") or item.get("url")
        if url:
            urls.append(url)
    return urls


# ── Informe y CLI ────────────────────────────────────────────────────────────

def render(plan: Plan, definicion: Definicion, tablero: str, aplicar: bool) -> str:
    lineas = [f"Tablero: {tablero}", f"Marcadores declarados por specs sincronizables: {len(definicion)}", ""]

    if plan.anadir:
        lineas.append(f"AÑADIR — {len(plan.anadir)}")
        lineas += [f"  {marca:<14} #{numero}" for marca, numero, _ in plan.anadir]
    else:
        lineas.append("AÑADIR — 0 (el tablero ya tiene todo lo que declaran las specs)")

    lineas.append("")
    lineas.append(f"YA PRESENTES — {len(plan.presentes)}")

    if plan.sin_issue:
        lineas += [
            "",
            f"SIN ISSUE — {len(plan.sin_issue)}: las specs los declaran y no existen.",
            "  No es cosa de este script: ejecuta `/sdd-sync --apply` primero.",
        ]
        lineas += [f"  {m}" for m in plan.sin_issue]

    if definicion.ignoradas:
        lineas += ["", "SPECS IGNORADAS (no sincronizan por su estado):"]
        lineas += [f"  {nombre} — {estado}" for nombre, estado in definicion.ignoradas]

    if plan.hay_trabajo and not aplicar:
        lineas += ["", "Esto es un plan. Vuelve a ejecutar con --apply para aplicarlo."]
    return "\n".join(lineas)


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true", help="aplica; sin esto solo enseña el plan")
    p.add_argument("--owner", default=OWNER_POR_DEFECTO)
    p.add_argument("--repo", default=REPO_POR_DEFECTO)
    p.add_argument("--project", default=TABLERO_POR_DEFECTO, help="título del tablero")
    args = p.parse_args(argv)

    definicion = leer_definicion()
    try:
        numero = numero_de_tablero(args.owner, args.project)
        indice = indexar_issues(issues_gestionables(args.repo))
        plan = planificar(definicion, indice, urls_del_tablero(args.owner, numero))
    except GhNoDisponible as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    print(render(plan, definicion, args.project, args.apply))

    if not args.apply or not plan.hay_trabajo:
        return 0

    fallos = 0
    for marca, numero_issue, url in plan.anadir:
        try:
            gh("project", "item-add", str(numero), "--owner", args.owner, "--url", url)
            print(f"  + {marca} (#{numero_issue})")
        except RuntimeError as error:
            fallos += 1
            print(f"  ! {marca} (#{numero_issue}): {error}", file=sys.stderr)
    print(f"\nAñadidos {len(plan.anadir) - fallos} de {len(plan.anadir)}.")
    return 1 if fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
