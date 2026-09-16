#!/usr/bin/env python3
"""Genera la guía para colaboradores «AlejandrIA por dentro».

La página es un HTML autocontenido: proyecto, arquitectura explorable, tareas abiertas
en un Gantt sin fechas con sus dependencias, y cómo trabajar.

De dónde sale cada cosa, para que no haya dos fuentes de verdad:

* **Specs** (`docs/specs/SPEC-*.md`): épicas, tareas, severidad, dependencias y los
  criterios de aceptación. Se leen del bloque `sdd-sync` y de la sección 3, igual que
  hace `/sdd-sync`. Una tarea nueva en una spec `Ready` aparece sola.
* **GitHub** (`gh`): número de issue y si está abierto o cerrado. Se guarda una copia
  en `docs/onboarding/issues.json` para poder regenerar sin red (`--sin-github`).
* **`docs/onboarding/tareas.yaml`**: lo que ayuda a ejecutar y no está en la spec
  (alcance explicado, archivos, «ojo con», rama sugerida, reparto).
* **`docs/onboarding/arquitectura.yaml`**: componentes, recorrido de una ejecución y
  agentes del pipeline.

Uso (desde la raíz del repo):
    python scripts/build_onboarding.py                 # estado de issues desde GitHub
    python scripts/build_onboarding.py --sin-github    # usa docs/onboarding/issues.json
    python scripts/build_onboarding.py --estricto      # avisos de coherencia = error

Salida por defecto: docs/public/onboarding/alejandria-por-dentro.html
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "docs" / "specs"
ONB = ROOT / "docs" / "onboarding"
CACHE = ONB / "issues.json"
SALIDA = ROOT / "docs" / "public" / "onboarding" / "alejandria-por-dentro.html"
REPO = "luxinopanyvino/swarm-platform-builder"
REPO_URL = f"https://github.com/{REPO}"
SPEC_URL = f"{REPO_URL}/blob/develop/docs/specs/"
TABLERO_URL = "https://github.com/users/luxinopanyvino/projects/8"
ACTIVAS = {"ready", "in progress", "done"}


# ── Lectura de specs ────────────────────────────────────────────────────────
def md_a_html(texto: str) -> str:
    """El markdown mínimo de los criterios de aceptación: enlaces, código, negrita, cursiva."""
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"<em>\1</em>", t)
    return t


def criterios(texto: str) -> dict[str, str]:
    """AC de la sección 3 de una spec: `- [ ] **AC1** — texto` con líneas de continuación.

    La sección es `## 3. Criterios…`, no cualquier `## 3.x`: SPEC-031 tiene un
    `## 3.0 Preguntas abiertas` antes, y tomar el primer «3.» dejaba sin criterios.
    """
    m = (re.search(r"^## 3\.\s+Criterios.*?$(.*?)(?=^## |\Z)", texto, re.S | re.M)
         or re.search(r"^## 3\.\s.*?$(.*?)(?=^## |\Z)", texto, re.S | re.M))
    if not m:
        return {}
    acs: dict[str, str] = {}
    actual = None
    for linea in m.group(1).splitlines():
        ini = re.match(r"^- \[[ xX]\] \*\*(AC\d+)\*\*\s*[—–-]?\s*(.*)$", linea)
        if ini:
            actual = ini.group(1)
            acs[actual] = ini.group(2).strip()
        elif actual and linea.startswith("  ") and linea.strip():
            acs[actual] += " " + linea.strip()
        elif not linea.strip():
            actual = None
    return acs


def leer_specs() -> list[dict]:
    specs = []
    for ruta in sorted(SPECS.glob("SPEC-*.md")):
        texto = ruta.read_text(encoding="utf-8")
        bloque = re.search(r"```yaml\s*\n(# sdd-sync v1.*?)```", texto, re.S)
        if not bloque:
            continue
        datos = yaml.safe_load(bloque.group(1)) or {}
        estado = re.search(r"^- \*\*Estado:\*\*\s*([^\n]+)$", texto, re.M)
        estado = (estado.group(1).strip() if estado else "").lower()
        specs.append(dict(
            id="-".join(ruta.stem.split("-")[:2]), archivo=ruta.name,
            estado=next((e for e in ACTIVAS | {"draft", "superseded"} if estado.startswith(e)), estado),
            epica=datos.get("epic") or {}, tareas=datos.get("tasks") or [], acs=criterios(texto),
        ))
    return specs


# ── GitHub ──────────────────────────────────────────────────────────────────
def gh_bin() -> str | None:
    encontrado = shutil.which("gh")
    if encontrado:
        return encontrado
    for candidato in (Path(r"C:\Program Files\GitHub CLI\gh.exe"), Path("/c/Program Files/GitHub CLI/gh.exe")):
        if candidato.exists():
            return str(candidato)
    return None


def issues_github() -> dict[str, dict]:
    gh = gh_bin()
    if not gh:
        raise RuntimeError("no encuentro `gh`: instálalo y autentícate, o usa --sin-github")
    res: dict[str, dict] = {}
    for etiqueta in ("epic", "task"):
        salida = subprocess.run(
            [gh, "issue", "list", "-R", REPO, "--state", "all", "--label", etiqueta,
             "--limit", "1000", "--json", "number,state,body"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout
        for issue in json.loads(salida):
            marca = re.search(r"<!--\s*sdd:(?:epic|task):([ET][\d.]+)\s*-->", issue.get("body") or "")
            if marca:
                res[marca.group(1)] = {"n": issue["number"], "estado": issue["state"].lower()}
    return dict(sorted(res.items(), key=lambda kv: orden_id(kv[0])))


def orden_id(i: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", i))


# ── Modelo ──────────────────────────────────────────────────────────────────
def construir(specs, issues, editorial, arq, avisos):
    fichas = editorial.get("tareas") or {}
    ep_ed = editorial.get("epicas") or {}
    comps = {c["id"]: c for c in arq["componentes"]}

    activas = [s for s in specs if s["estado"] in ACTIVAS]
    todas: dict[str, dict] = {}
    epicas: dict[str, dict] = {}
    for s in activas:
        eid = s["epica"].get("id")
        epicas.setdefault(eid, dict(id=eid, nombre=s["epica"].get("title", eid), area=s["epica"].get("area", ""),
                                    spec=SPEC_URL + s["archivo"], specid=s["id"],
                                    n=(issues.get(eid) or {}).get("n"),
                                    corto=(ep_ed.get(eid) or {}).get("corto") or " ".join(s["epica"].get("title", eid).split()[:2])))
        for t in s["tareas"]:
            gh = issues.get(t["id"]) or {}
            f = fichas.get(t["id"]) or {}
            dod = []
            for ac in t.get("acceptance") or []:
                if ac in s["acs"]:
                    dod.append(f'{md_a_html(s["acs"][ac])} <span class="ac">{ac}</span>')
                else:
                    avisos.append(f'{t["id"]}: el criterio {ac} no está en la sección 3 de {s["id"]}')
            dod += list(f.get("hecha_cuando_extra") or [])
            for c in f.get("componentes") or []:
                if c not in comps:
                    avisos.append(f'{t["id"]}: componente desconocido «{c}» en tareas.yaml')
            todas[t["id"]] = dict(
                id=t["id"], epic=eid, title=t["title"], sev=t.get("sev", "medium"),
                deps=[str(d) for d in t.get("depends_on") or []], n=gh.get("n"),
                issue_estado=gh.get("estado"), implementada=f.get("estado") == "implementada",
                short=f.get("corto") or (t["title"][:22] + "…" if len(t["title"]) > 23 else t["title"]),
                alcance=f.get("alcance") or f'Sin ficha todavía: lee la tarea en <a href="{SPEC_URL}{s["archivo"]}">{s["id"]}</a>.',
                dod=dod, files=f.get("archivos") or [], cuidado=f.get("ojo_con") or "",
                rama=f.get("rama") or "", sensible=f.get("revision"),
                comps=[c for c in f.get("componentes") or [] if c in comps],
                ficha=bool(f),
            )

    for tid in fichas:
        if tid not in todas:
            avisos.append(f"tareas.yaml tiene una ficha para {tid}, que no está en ninguna spec activa")

    cerradas = {i for i, t in todas.items() if t["issue_estado"] == "closed"}
    abiertas = {i: t for i, t in todas.items() if i not in cerradas}

    memo: dict[str, int] = {}

    def ola(i: str) -> int:
        if i not in memo:
            pend = [d for d in todas[i]["deps"] if d in abiertas]
            memo[i] = 1 + max(ola(d) for d in pend) if pend else 0
        return memo[i]

    for i, t in abiertas.items():
        for d in t["deps"]:
            if d not in todas and not d.startswith("#"):
                avisos.append(f"{i}: depende de {d}, que no existe en las specs activas")
        t["deps"] = [d for d in t["deps"] if d in todas]
        t["ola"] = ola(i)
        if t["n"] is None:
            t["estado"] = "sin-issue"
        elif t["implementada"]:
            t["estado"] = "hecha"
        elif all(d in cerradas for d in t["deps"]):
            t["estado"] = "lista"
        else:
            t["estado"] = "espera"
        t["unlocks"] = [u for u, x in abiertas.items() if i in x["deps"]]
        if not t["ficha"]:
            avisos.append(f"{i}: sin ficha en tareas.yaml (sale con lo mínimo)")

    orden = sorted(abiertas.values(), key=lambda t: orden_id(t["id"]))
    epicas_vis = [epicas[e] for e in sorted({t["epic"] for t in orden}, key=orden_id)]

    reparto = []
    asignadas = set()
    for g in editorial.get("reparto") or []:
        ids = []
        for i in g.get("tareas") or []:
            if i not in todas:
                avisos.append(f"reparto «{g.get('nombre')}»: {i} no existe en las specs activas")
            elif i in abiertas:
                ids.append(i)
                asignadas.add(i)
        reparto.append(dict(nombre=g.get("nombre", ""), foco=g.get("foco", ""), tareas=ids))
    sin = [t["id"] for t in orden if t["id"] not in asignadas]
    if sin:
        reparto.append(dict(nombre="Sin asignar", foco="tareas nuevas que aún no están en el reparto", tareas=sin))
    reparto = [g for g in reparto if g["tareas"]]

    borradores = []
    for s in specs:
        # Un Draft que amplía una épica ya activa (p. ej. SPEC-024 sobre E2) no es
        # una «épica en borrador»: sus tareas entrarán en esa épica al sincronizar.
        if s["estado"] == "draft" and s["epica"].get("id") and s["epica"]["id"] not in epicas:
            eid = s["epica"]["id"]
            borradores.append(dict(id=eid, nombre=s["epica"].get("title", eid), spec=SPEC_URL + s["archivo"], specid=s["id"],
                                   tareas=[dict(id=t["id"], title=t["title"]) for t in s["tareas"]],
                                   nota=(ep_ed.get(eid) or {}).get("nota_borrador", "")))

    ref_cerradas = {d: dict(title=todas[d]["title"], n=todas[d]["n"]) for t in orden for d in t["deps"] if d in cerradas}
    campos = ("id", "n", "sev", "deps", "unlocks", "title", "short", "epic", "alcance", "dod", "files",
              "cuidado", "rama", "sensible", "comps", "estado", "ola")
    return dict(
        tareas=[{k: t[k] for k in campos} for t in orden], epicas=epicas_vis, reparto=reparto,
        cerradas=ref_cerradas, borradores=borradores,
        n_cerradas=len(cerradas), n_listas=sum(1 for t in orden if t["estado"] == "lista"),
    )


# ── HTML ────────────────────────────────────────────────────────────────────
def pipeline_svg(agentes) -> str:
    xs = [16 + i * 188 for i in range(len(agentes))]
    y, w, h = 62, 152, 54
    ancho = xs[-1] + w + 16
    p = [f'<svg viewBox="0 0 {ancho} 170" role="img" aria-label="Pipeline de AlejandrIA: '
         + ", ".join(a["nombre"] for a in agentes)
         + ' en secuencia; el revisor devuelve el borrador al redactor si la nota es menor que 80, como mucho tres veces.">',
         '<defs><marker id="pflecha" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="7" markerHeight="7" orient="auto">'
         '<path d="M0,0 L8,4 L0,8 z" class="p-flecha"/></marker></defs>']
    ids = [a["id"] for a in agentes]
    if "revisor" in ids and "redactor" in ids:
        r, d = xs[ids.index("revisor")], xs[ids.index("redactor")]
        p.append(f'<path class="p-bucle" d="M{r + 76} {y} C{r + 76} 14, {d + 76} 14, {d + 76} {y - 2}" marker-end="url(#pflecha)"/>')
        p.append(f'<text class="p-etq" x="{(r + d) // 2 + 76}" y="22" text-anchor="middle">nota &lt; 80 → vuelve · máx. 3 vueltas</text>')
    for i, a in enumerate(agentes):
        x = xs[i]
        if i < len(agentes) - 1:
            p.append(f'<path class="p-linea" d="M{x + w} {y + h // 2} H{xs[i + 1]}" marker-end="url(#pflecha)"/>')
        p.append(f'<g class="p-agente" data-agente="{a["id"]}" tabindex="0" role="button" aria-label="{html.escape(a["nombre"])}: ver detalle">'
                 f'<rect class="p-caja" x="{x}" y="{y}" width="{w}" height="{h}" rx="6"/>'
                 f'<text class="p-num" x="{x + 12}" y="{y + 20}">{i + 1}</text>'
                 f'<text class="p-nombre" x="{x + 12}" y="{y + 40}">{html.escape(a["nombre"])}</text></g>')
        if a.get("pie"):
            p.append(f'<text class="p-sub" x="{x + 76}" y="{y + h + 26}" text-anchor="middle">{html.escape(a["pie"])}</text>')
    p.append("</svg>")
    return "\n".join(p)


def comp_html(c) -> str:
    cls = "comp nuevo" if c.get("nuevo") else "comp"
    return (f'<button type="button" class="{cls}" data-comp="{c["id"]}" id="comp-{c["id"]}" aria-pressed="false">'
            f'<span class="comp-nombre">{html.escape(c["nombre"])}</span>'
            f'<span class="comp-ruta">{html.escape(c["ruta"])}</span><span class="comp-tareas"></span></button>')


def cmd(texto: str, etiqueta: str = "") -> str:
    lab = f'<span class="cmd-lab">{etiqueta}</span>' if etiqueta else ""
    return (f'<div class="cmd">{lab}<code>{html.escape(texto)}</code>'
            f'<button type="button" class="btn btn-mini" data-copiar>Copiar</button></div>')


def pagina(modelo, arq, hoy: str) -> str:
    plantilla = ONB / "plantilla"
    css = (plantilla / "estilos.css").read_text(encoding="utf-8")
    js = (plantilla / "app.js").read_text(encoding="utf-8")
    comps = arq["componentes"]
    capas_html = "".join(
        f'<div class="capa capa-{i}"><div class="capa-nombre">{html.escape(nombre)}</div>'
        f'<div class="capa-comps">{"".join(comp_html(c) for c in comps if c["capa"] == i)}</div></div>'
        for i, nombre in enumerate(arq["capas"][:4]))
    lateral_html = "".join(comp_html(c) for c in comps if c["capa"] == 4)
    tareas = modelo["tareas"]
    ej = next((t for t in tareas if t["estado"] == "lista" and t["n"]), tareas[0] if tareas else None)
    ej_n = ej["n"] if ej and ej["n"] else 352
    datos = dict(
        repo=REPO_URL, tablero=TABLERO_URL, tareas=tareas, epicas=modelo["epicas"], reparto=modelo["reparto"],
        cerradas=modelo["cerradas"], capas=arq["capas"],
        comps={c["id"]: dict(nombre=c["nombre"], ruta=c["ruta"], que=c["que"], reglas=c.get("reglas") or [],
                             rel=[[r["con"], r["como"]] for r in c.get("relaciones") or []], nuevo=bool(c.get("nuevo")), capa=c["capa"])
               for c in comps},
        recorrido=[dict(ids=r["componentes"], txt=r["texto"]) for r in arq["recorrido"]],
        agentes=arq["agentes"],
    )
    borr = "".join(
        f'<div class="borrador"><p class="mini-tit">Fuera del diagrama · {b["id"]} en borrador</p>'
        f'<h3>{html.escape(b["nombre"])}</h3>'
        f'<p>La spec (<a href="{b["spec"]}">{b["specid"]}</a>) está en <code>Draft</code> y no genera issues. {b["nota"]}</p>'
        + (f'<p class="nota">Tareas previstas: {" → ".join(f"<span class=mono>{t["id"]}</span> {html.escape(t["title"])}" for t in b["tareas"])}</p>' if b["tareas"] else "")
        + "</div>" for b in modelo["borradores"])
    n_ep = len(modelo["epicas"])

    return f'''<title>AlejandrIA por dentro</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;600&display=swap">
<style>
{css}
</style>

<header class="barra">
  <div class="barra-in">
    <a class="marca" href="#inicio">Alejandr<span>IA</span> <em>por dentro</em></a>
    <nav aria-label="Secciones">
      <a href="#proyecto">Proyecto</a><a href="#arquitectura">Arquitectura</a><a href="#tareas">Tareas</a><a href="#trabajar">Cómo trabajar</a>
    </nav>
  </div>
</header>

<div class="pagina">
<section class="inicio" id="inicio">
  <div class="inicio-txt">
    <p class="eyebrow">Guía para quien empieza · generada el {hoy}</p>
    <h1>Una plataforma para orquestar agentes, y la revista científica que la pone a prueba</h1>
    <p class="entradilla">FastAPI, LangGraph y Qdrant por detrás; React por delante. Aquí tienes qué hace el proyecto, cómo está construido, qué trabajo queda abierto con sus dependencias y cómo ejecutarlo desde la terminal. Casi todo se puede pulsar.</p>
  </div>
  <dl class="cifras">
    <div><dt>Agentes en el pipeline</dt><dd>{len(arq["agentes"])}</dd></div>
    <div><dt>Épicas abiertas</dt><dd>{n_ep}</dd></div>
    <div><dt>Tareas abiertas</dt><dd>{len(tareas)}</dd></div>
    <div><dt>Listas para empezar</dt><dd>{modelo["n_listas"]}</dd></div>
  </dl>
</section>

<section class="seccion" id="proyecto">
  <div class="seccion-cab">
    <p class="eyebrow">1 · El proyecto</p>
    <h2>Qué es y qué produce</h2>
  </div>
  <div class="proyecto-grid">
    <div class="prosa">
      <p><strong>swarm-platform-builder</strong> es una plataforma para definir y ejecutar equipos de agentes de IA. Cada agente tiene un perfil, unas capacidades (buscar en documentos, llamar a un modelo, dar formato…) y un lugar en un grafo. El grafo no está escrito en Python: es un <strong>dato</strong>, un <code>template.yaml</code> por proyecto.</p>
      <p>El proyecto de referencia es <strong>AlejandrIA Magazine</strong>: cinco agentes que investigan, redactan, revisan, formatean y publican artículos científicos. Es a la vez producto y banco de pruebas: lo que la plataforma promete (aislamiento entre proyectos, trazabilidad, evaluación) se demuestra sobre él.</p>
      <div class="aviso-doble">
        <p class="aviso-tit">Dos sentidos de «agente» conviven en el repo</p>
        <p><strong>Agentes de producto</strong>: los del pipeline, perfiles en base de datos y en <code>*.agent.md</code>. Son la funcionalidad.<br><strong>Agentes de desarrollo</strong>: <code>.claude/agents/</code> (<code>task-runner</code>, <code>sdd-sync</code>), que implementan y sincronizan el backlog. Son herramientas del repo.</p>
      </div>
    </div>
    <div class="pipeline">
      <p class="mini-tit">El pipeline de AlejandrIA · pulsa un agente</p>
      <div class="pipeline-svg">{pipeline_svg(arq["agentes"])}</div>
      <div class="agente-info" id="agente-info" aria-live="polite"></div>
    </div>
  </div>
  <div class="flujo-trabajo">
    <p class="mini-tit">Cómo nace el trabajo que vas a hacer</p>
    <ol class="cadena">
      <li><span class="cad-n">Spec</span><span class="cad-t"><code>docs/specs/</code>: problema, criterios de aceptación y bloque de tareas</span></li>
      <li><span class="cad-n">/sdd-sync</span><span class="cad-t">convierte las tareas de la spec en issues del tablero</span></li>
      <li><span class="cad-n">/resolve-task</span><span class="cad-t">implementa un issue: rama, código, tests, bitácora y PR</span></li>
      <li><span class="cad-n">Revisión</span><span class="cad-t">PR contra <code>develop</code> con CI en verde y aprobación</span></li>
      <li><span class="cad-n">Merge</span><span class="cad-t"><code>Closes #N</code> cierra el issue y desbloquea lo que dependía de él</span></li>
    </ol>
  </div>
</section>

<section class="seccion" id="arquitectura">
  <div class="seccion-cab">
    <p class="eyebrow">2 · Arquitectura</p>
    <h2>Cómo está construido</h2>
    <p class="lead">Cuatro capas y tres piezas transversales. Pulsa un componente para ver qué hace, las reglas que no conviene romper y las tareas abiertas que lo tocan. Para verlo en movimiento, recorre una ejecución paso a paso.</p>
  </div>
  <div class="recorrido" id="recorrido">
    <button type="button" class="btn btn-primario" id="rec-empezar">Recorrer una ejecución</button>
    <div class="rec-ctl" hidden>
      <button type="button" class="btn" id="rec-prev">Anterior</button>
      <span class="rec-cont" id="rec-cont"></span>
      <button type="button" class="btn btn-primario" id="rec-next">Siguiente</button>
      <button type="button" class="btn btn-texto" id="rec-salir">Salir del recorrido</button>
    </div>
    <p class="rec-txt" id="rec-txt" aria-live="polite" hidden></p>
  </div>
  <div class="arq">
    <div class="arq-diagrama">
      <div class="arq-capas">{capas_html}</div>
      <div class="arq-lateral"><div class="capa-nombre">{html.escape(arq["capas"][4])}</div><div class="lateral-comps">{lateral_html}</div></div>
    </div>
    <aside class="arq-panel" id="arq-panel" aria-live="polite"></aside>
  </div>
</section>

<section class="seccion" id="tareas">
  <div class="seccion-cab">
    <p class="eyebrow">3 · Trabajo abierto</p>
    <h2>Tareas y dependencias</h2>
    <p class="lead">Un Gantt sin fechas: la posición no es un día, es <strong>cuándo se puede empezar</strong>. <em>Por olas</em> coloca cada tarea en cuanto se desbloquea; <em>Por persona</em> muestra el reparto, en orden. Pasa por encima de una tarea para ver su cadena de dependencias; púlsala para abrir su ficha, con el comando para ejecutarla.</p>
  </div>
  <div class="controles" role="group" aria-label="Controles del diagrama">
    <div class="seg" role="radiogroup" aria-label="Vista">
      <button type="button" role="radio" aria-checked="true" data-modo="olas" id="modo-olas">Por olas</button>
      <button type="button" role="radio" aria-checked="false" data-modo="persona" id="modo-persona">Por persona</button>
    </div>
    <div class="filtros" id="filtro-epicas" aria-label="Épicas"></div>
    <div class="filtros" id="filtro-sev" aria-label="Severidad"></div>
    <label class="interruptor" for="solo-listas"><input type="checkbox" id="solo-listas"> Solo listas para empezar</label>
    <label class="buscar" for="buscar"><span class="sr">Buscar tarea</span><input type="search" id="buscar" placeholder="Buscar: T17, hash, #353…" autocomplete="off"></label>
  </div>
  <div class="filtro-activo" id="filtro-comp" hidden></div>
  <div class="leyenda">
    <span><i class="lg lg-lista"></i>Lista para empezar</span>
    <span><i class="lg lg-espera"></i>Espera a otra tarea</span>
    <span><i class="lg lg-hecha"></i>Hecha, falta cerrar el issue</span>
    <span><i class="lg lg-sin"></i>Sin issue todavía</span>
    <span><i class="lg-sev sev-high"></i>Alta <i class="lg-sev sev-medium"></i>Media <i class="lg-sev sev-low"></i>Baja</span>
    <span><i class="lg-rev">R</i>Pide revisión de alguien con experiencia</span>
  </div>
  <div class="gantt-marco"><div class="gantt-scroll" tabindex="0" aria-label="Diagrama de tareas"><div class="gantt" id="gantt"></div></div></div>
  <p class="nota" id="gantt-nota"></p>
  {borr}
</section>

<section class="seccion" id="trabajar">
  <div class="seccion-cab">
    <p class="eyebrow">4 · Cómo trabajar</p>
    <h2>Del issue a la PR, y del plan a la página</h2>
    <p class="lead">Tres cosas que vas a hacer a menudo. Todos los comandos se lanzan <strong>desde la raíz del repositorio</strong>; los que empiezan por <code>/</code> se escriben dentro de Claude Code.</p>
  </div>

  <div class="pestanas" role="tablist" aria-label="Guías">
    <button type="button" role="tab" id="tab-ejecutar" aria-controls="panel-ejecutar" aria-selected="true">Ejecutar una tarea</button>
    <button type="button" role="tab" id="tab-anadir" aria-controls="panel-anadir" aria-selected="false" tabindex="-1">Añadir tareas o épicas</button>
    <button type="button" role="tab" id="tab-pagina" aria-controls="panel-pagina" aria-selected="false" tabindex="-1">Actualizar esta página</button>
    <button type="button" role="tab" id="tab-referencia" aria-controls="panel-referencia" aria-selected="false" tabindex="-1">Skills y comandos</button>
  </div>

  <div class="panel-guia" role="tabpanel" id="panel-ejecutar" aria-labelledby="tab-ejecutar">
    <div class="guia-grid">
      <div>
        <h3>Antes de la primera vez</h3>
        <ol class="pasos">
          <li>Instala <strong>Claude Code</strong> (la CLI <code>claude</code> o la extensión de VS Code) y <strong>GitHub CLI</strong>.</li>
          <li>Autentica <code>gh</code> con permisos de proyecto. Si acabas de instalarlo, cierra y abre VS Code para que la terminal lo encuentre.
            {cmd("gh auth login --scopes project")}</li>
          <li>Comprueba que ves los issues: {cmd("gh issue view " + str(ej_n) + " -R " + REPO)}</li>
        </ol>
        <h3>Ejecutarla con la skill <code>/resolve-task</code></h3>
        <ol class="pasos">
          <li>Elige una tarea <strong>lista para empezar</strong> en el diagrama y apunta su número de issue (la ficha lo trae).</li>
          <li>Abre Claude Code en la raíz del repo:
            {cmd("claude")}</li>
          <li>Escribe la skill con el número. Puedes pasar varios, y se resuelven en orden:
            {cmd("/resolve-task " + str(ej_n))}</li>
          <li>O, sin abrir la sesión interactiva (en Git Bash):
            {cmd("bash scripts/run-task.sh " + str(ej_n))}</li>
        </ol>
      </div>
      <div>
        <h3>Qué hace por dentro</h3>
        <ol class="pasos">
          <li>Lee el issue: criterios, dependencias («Bloqueada por: #N»), área y severidad.</li>
          <li><strong>Comprueba que todas las dependencias estén cerradas.</strong> Si alguna sigue abierta, se detiene y lo avisa: no implementa tareas bloqueadas.</li>
          <li>Crea una rama con prefijo desde <code>develop</code> y lee el código implicado.</li>
          <li>Implementa y ejecuta los tests. Si fallan, no sigue.</li>
          <li>Escribe la bitácora en <code>docs/bitacora/tarea-N.md</code>.</li>
          <li>Sube la rama y abre la PR contra <code>develop</code> con <code>Closes #N</code>. <strong>No mergea</strong> ni cierra issues.</li>
        </ol>
        <h3>Y después, tú</h3>
        <ul class="dod">
          <li>Revisa el diff como si lo hubiera escrito otra persona: es tu PR.</li>
          <li>Comprueba que la CI está en verde y que cada criterio de la ficha se cumple.</li>
          <li>Pide revisión; si la ficha lleva <span class="lg-rev">R</span>, a alguien con experiencia.</li>
          <li>Cuando se mergee, el issue se cierra solo y las tareas que dependían de él quedan listas. Regenera esta página.</li>
        </ul>
        <p class="aviso">Una tarea implementada pero con el issue abierto <strong>sigue bloqueando</strong> a las que dependen de ella: <code>/resolve-task</code> se detendrá. Ciérrala por el flujo (PR con su bitácora) antes de seguir.</p>
      </div>
    </div>
  </div>

  <div class="panel-guia" role="tabpanel" id="panel-anadir" aria-labelledby="tab-anadir" hidden>
    <p class="aviso"><strong>Nunca crees issues a mano.</strong> El tablero se genera desde las specs: un issue sin su marcador oculto (<code>&lt;!-- sdd:task:T16.2 --&gt;</code>) queda «no gestionado», y uno duplicado bloquea la sincronización.</p>
    <div class="guia-grid">
      <div>
        <h3>Una tarea nueva en una épica que ya existe</h3>
        <ol class="pasos">
          <li>Crea una rama <code>docs/</code> y abre la spec de la épica (la ficha de cualquier tarea de la épica enlaza su spec).</li>
          <li>Si la tarea necesita un criterio que no existe, añádelo en la sección 3 como <code>- [ ] **AC8** — *Given* …, *When* …, *Then* …</code></li>
          <li>Añádela al bloque <code>sdd-sync</code> de la sección 8:
            <pre class="bloque-code">  - id: T16.7
    title: "Qué hay que hacer, en una frase"
    sev: medium            # high · medium · low
    depends_on: [T16.5]    # ids de tareas; [] si ninguna
    acceptance: [AC8]</pre></li>
          <li>Valida las specs: {cmd("python scripts/validate_specs.py")}</li>
          <li>PR contra <code>develop</code>. Cuando esté mergeada, en Claude Code, primero simula y luego aplica:
            {cmd("/sdd-sync")}{cmd("/sdd-sync --apply")}</li>
          <li>Opcional pero recomendable: su ficha en <code>docs/onboarding/tareas.yaml</code> (alcance, archivos, «ojo con», rama) y su sitio en el reparto. Regenera la página.</li>
        </ol>
      </div>
      <div>
        <h3>Una épica nueva</h3>
        <ol class="pasos">
          <li>Crea la spec con la skill de Spec Kit. Nace en <code>Draft</code> con su bloque <code>sdd-sync</code>:
            {cmd('/speckit-specify "Descripción de la necesidad"')}</li>
          <li>Madúrala: preguntas a lo que quedó ambiguo, checklist de calidad de requisitos y análisis de consistencia con su ADR y sus tareas:
            {cmd("/speckit-clarify SPEC-032")}{cmd("/speckit-checklist SPEC-032 seguridad")}{cmd("/speckit-analyze SPEC-032")}</li>
          <li>Cambia su <strong>Estado</strong> a <code>Ready</code>. Las specs en <code>Draft</code> no generan issues.</li>
          <li>Valida, abre la PR <code>docs/</code> y, tras el merge, <code>/sdd-sync</code> y <code>/sdd-sync --apply</code>.</li>
          <li>Cada épica va a su tablero: <strong>E14 en adelante</strong> al <a href="{TABLERO_URL}">roadmap</a>; E1–E13, al backlog antiguo.</li>
          <li>Añade su nombre corto en <code>epicas</code> de <code>tareas.yaml</code> y regenera la página.</li>
        </ol>
        <p class="nota">El número de spec y de épica es el siguiente libre. <code>/speckit-specify</code> lo propone, y la validación de specs falla si dos épicas se pisan.</p>
      </div>
    </div>
  </div>

  <div class="panel-guia" role="tabpanel" id="panel-pagina" aria-labelledby="tab-pagina" hidden>
    <div class="guia-grid">
      <div>
        <h3>Regenerarla</h3>
        <ol class="pasos">
          <li>Desde la raíz del repo, con <code>gh</code> autenticado (lee el estado de cada issue):
            {cmd("python scripts/build_onboarding.py")}</li>
          <li>Sin red o sin <code>gh</code>, usa la última copia guardada del estado:
            {cmd("python scripts/build_onboarding.py --sin-github")}</li>
          <li>Ábrela en el navegador: <code>docs/public/onboarding/alejandria-por-dentro.html</code>. También la sirve la web de documentación:
            {cmd("cd docs && npm install && npm run dev", "luego")}<span class="nota">y entra en <code>http://localhost:5174/onboarding/alejandria-por-dentro.html</code></span></li>
          <li>Guarda el cambio en una rama <code>docs/</code> con su PR, como cualquier otro.</li>
        </ol>
        <h3>Cuándo regenerarla</h3>
        <ul class="dod">
          <li>Después de <code>/sdd-sync --apply</code> (tareas o épicas nuevas).</li>
          <li>Después de mergear PRs que cierran tareas (cambian las listas para empezar).</li>
          <li>Al cambiar el reparto, una ficha o la arquitectura.</li>
        </ul>
      </div>
      <div>
        <h3>De dónde sale cada cosa</h3>
        <table class="origen">
          <thead><tr><th scope="col">Lo que ves</th><th scope="col">Se edita en</th></tr></thead>
          <tbody>
            <tr><td>Épicas, tareas, severidad, dependencias, «Hecha cuando»</td><td><code>docs/specs/SPEC-*.md</code> (bloque <code>sdd-sync</code> y sección 3)</td></tr>
            <tr><td>Número de issue, abierta o cerrada</td><td>GitHub; copia en <code>docs/onboarding/issues.json</code></td></tr>
            <tr><td>Alcance, archivos, «Ojo con», rama, revisión, nombre corto, reparto</td><td><code>docs/onboarding/tareas.yaml</code></td></tr>
            <tr><td>Arquitectura, recorrido de una ejecución, agentes</td><td><code>docs/onboarding/arquitectura.yaml</code></td></tr>
            <tr><td>Aspecto y comportamiento de la página</td><td><code>docs/onboarding/plantilla/</code> (<code>estilos.css</code>, <code>app.js</code>)</td></tr>
          </tbody>
        </table>
        <p class="nota">El generador avisa de lo que no cuadra: fichas de tareas que ya no existen, componentes desconocidos, criterios que faltan en la spec o tareas sin ficha. Con <code>--estricto</code>, esos avisos son error; así lo ejecuta el test <code>test_onboarding_page.py</code>.</p>
        <h3>Si está publicada como artifact</h3>
        <p>Pide a Claude Code que la republique en el mismo enlace, pasándole la URL: «republica el artifact &lt;URL&gt; con <code>docs/public/onboarding/alejandria-por-dentro.html</code>». Los que ya la tengan abierta verán la versión nueva.</p>
      </div>
    </div>
  </div>

  <div class="panel-guia" role="tabpanel" id="panel-referencia" aria-labelledby="tab-referencia" hidden>
    <div class="tabla-scroll">
    <table class="origen referencia">
      <thead><tr><th scope="col">Skill o comando</th><th scope="col">Para qué</th><th scope="col">Cuándo</th></tr></thead>
      <tbody>
        <tr><td><code>/resolve-task N [N…]</code></td><td>Implementa issues de extremo a extremo con el agente <code>task-runner</code>: rama, código, tests, bitácora y PR.</td><td>Para ejecutar una tarea lista.</td></tr>
        <tr><td><code>bash scripts/run-task.sh N</code></td><td>Lo mismo, sin sesión interactiva (<code>claude -p</code>).</td><td>Desde Git Bash o un script.</td></tr>
        <tr><td><code>/sdd-sync</code></td><td>Simula la sincronización specs → issues: qué crearía, actualizaría o está desalineado. No cambia nada.</td><td>Antes de aplicar, y para revisar el estado.</td></tr>
        <tr><td><code>/sdd-sync --apply</code></td><td>Crea y actualiza issues, dependencias, sub-issues y pertenencia al tablero. Nunca cierra ni borra.</td><td>Tras mergear cambios en specs.</td></tr>
        <tr><td><code>/speckit-specify</code></td><td>Crea una spec nueva en <code>Draft</code> desde la plantilla, con bloque <code>sdd-sync</code>.</td><td>Para una épica nueva.</td></tr>
        <tr><td><code>/speckit-clarify</code></td><td>Hasta 5 preguntas sobre lo ambiguo, y graba las respuestas en la spec.</td><td>Antes de pasarla a <code>Ready</code>.</td></tr>
        <tr><td><code>/speckit-checklist</code></td><td>Checklist de calidad de los requisitos de una spec.</td><td>Antes de pasarla a <code>Ready</code>.</td></tr>
        <tr><td><code>/speckit-analyze</code></td><td>Consistencia entre spec, ADR y tareas (solo lectura).</td><td>Antes de sincronizar.</td></tr>
        <tr><td><code>python scripts/validate_specs.py</code></td><td>Valida formato y coherencia de todas las specs; es el gate de CI.</td><td>Antes de cada PR que toca specs.</td></tr>
        <tr><td><code>python scripts/build_onboarding.py</code></td><td>Regenera esta página.</td><td>Tras sincronizar o cerrar tareas.</td></tr>
        <tr><td><code>python -m evals.agent_behavior.gate</code></td><td>Gate de regresión de los agentes (desde <code>backend/</code>).</td><td>Si tocas agentes, prompts o el dispatcher.</td></tr>
      </tbody>
    </table>
    </div>
  </div>

  <div class="contrib">
    <div>
      <h3>Definition of Done común</h3>
      <ul class="dod">
        <li>Cumple <strong>todos</strong> los criterios de aceptación de la tarea.</li>
        <li>Tests automatizados que cubren el cambio, en verde en CI.</li>
        <li>Sin secretos en el diff; dependencias nuevas escaneadas.</li>
        <li>Documentación, spec o ADR actualizados si el cambio los afecta.</li>
        <li>Si toca agentes, prompts o el dispatcher: el gate EDD pasa, o la regresión se explica en la misma PR.</li>
        <li>Revisada y aprobada. Nadie mergea su propia PR ni cierra issues a mano.</li>
      </ul>
      <h3>Tu primera semana</h3>
      <ol class="pasos">
        <li>Lee <code>CLAUDE.md</code> y <code>docs/governance/GOVERNANCE.md</code>.</li>
        <li>Levanta todo con <code>dev-local.cmd</code> (Qdrant, backend <code>:8000</code>, frontend <code>:5173</code>) y entra con <code>admin@admin</code>.</li>
        <li>Pasa los tests del backend una vez, para saber qué es «verde».</li>
        <li>Primera PR: la tarea marcada como <em>hecha, falta cerrar</em>, para aprender el flujo sin riesgo.</li>
      </ol>
    </div>
    <div>
      <h3>Lo que ya nos ha mordido</h3>
      <ul class="avisos">
        <li><strong>Tests y base de datos.</strong> Un orden concreto de tests llegó a vaciar la base de desarrollo. <code>tests/conftest.py</code> lo impide ahora: no debilites esa guarda.</li>
        <li><strong>Modelos que razonan.</strong> <code>olmo-3:7b</code> razona aunque se le pida que no y puede devolver respuestas vacías. Usa <code>qwen3.5</code>.</li>
        <li><strong>Esquema.</strong> Nunca con SQL a mano. Revisa lo que genera <code>--autogenerate</code>: hay un ciclo de claves foráneas que no sabe ordenar.</li>
        <li><strong>Directo a develop.</strong> Un hook bloquea commits y push a <code>develop</code>. Si salta un mensaje de gobernanza, crea una rama.</li>
      </ul>
      <h3>Comandos de cada día</h3>
      {cmd("DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q", "backend/")}
      {cmd("npm run build && npm run build:public", "frontend/")}
      {cmd('alembic revision --autogenerate -m "..."', "backend/")}
    </div>
  </div>
</section>

<footer class="pie">Generada el {hoy} con <code>python scripts/build_onboarding.py</code> desde las specs de <code>develop</code> y el estado de GitHub ({modelo["n_cerradas"]} tareas ya cerradas no aparecen). El estado vivo está en el <a href="{TABLERO_URL}">tablero del roadmap</a>.</footer>
</div>

<div class="velo" id="velo" hidden></div>
<aside class="cajon" id="cajon" aria-label="Ficha de la tarea" hidden>
  <div class="cajon-cab">
    <span class="cajon-id" id="cajon-id"></span>
    <button type="button" class="btn btn-texto" id="cajon-cerrar" aria-label="Cerrar ficha">Cerrar</button>
  </div>
  <div class="cajon-cuerpo" id="cajon-cuerpo"></div>
</aside>

<script>
const DATA = {json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")};
{js}
</script>
'''


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sin-github", action="store_true", help="usa docs/onboarding/issues.json en vez de consultar GitHub")
    ap.add_argument("--estricto", action="store_true", help="los avisos de coherencia hacen fallar la generación")
    ap.add_argument("--salida", type=Path, default=SALIDA, help="ruta del HTML generado")
    args = ap.parse_args(argv)
    # La consola de Windows no es UTF-8 cuando la salida va a una tubería (CI, tests).
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")

    if args.sin_github:
        issues = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
        origen = f"copia local ({CACHE.relative_to(ROOT)})" if CACHE.exists() else "sin datos de GitHub"
    else:
        issues = issues_github()
        CACHE.write_text(json.dumps(issues, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        origen = "GitHub"

    editorial = yaml.safe_load((ONB / "tareas.yaml").read_text(encoding="utf-8")) or {}
    arq = yaml.safe_load((ONB / "arquitectura.yaml").read_text(encoding="utf-8")) or {}
    avisos: list[str] = []
    modelo = construir(leer_specs(), issues, editorial, arq, avisos)

    duros = [a for a in avisos if "sin ficha" not in a]
    for a in avisos:
        print(f"  aviso: {a}")
    if args.estricto and duros:
        print(f"ERROR: {len(duros)} aviso(s) de coherencia con --estricto", file=sys.stderr)
        return 1

    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(pagina(modelo, arq, date.today().strftime("%d/%m/%Y")), encoding="utf-8")
    print(f"ok  {args.salida}  ·  estado de issues: {origen}")
    print(f"    {len(modelo['epicas'])} épicas · {len(modelo['tareas'])} tareas abiertas · "
          f"{modelo['n_listas']} listas · {modelo['n_cerradas']} cerradas · {len(avisos)} aviso(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
