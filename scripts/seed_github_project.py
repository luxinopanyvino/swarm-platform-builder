#!/usr/bin/env python3
"""
Genera el GitHub Project "Hardening & Platform Backlog" de forma ATÓMICA y
JERÁRQUICA:

  1. Crea labels (epic, task, area/*, sev/*).
  2. Crea el Project v2 y lo enlaza al repositorio.
  3. Crea un campo single-select "Epic" (E1..E6).
  4. Crea las 6 épicas y sus 28 tareas como issues, las añade al proyecto y les
     asigna el campo "Epic".
  5. Establece relaciones **sub-issue** (épica → sus tareas), de modo que el
     tablero/issue muestre la jerarquía de forma nativa.

Tras ejecutarlo: en la UI del proyecto activa  View ▸ Group by ▸ Epic  (y, si
quieres, muestra sub-issues en la tabla).

Requisitos: gh CLI autenticado con scope `project` (o GH_TOKEN con ese scope).
Uso:        python scripts/seed_github_project.py
"""
import json
import re
import subprocess
import sys

OWNER = "luxinopanyvino"
REPO = "luxinopanyvino/swarm-platform-builder"
PROJECT_TITLE = "Hardening & Platform Backlog"
FIELD_NAME = "Epic"

LABELS = [
    ("epic", "5319e7", "Épica del backlog"),
    ("task", "0e8a16", "Tarea de implementación"),
    ("area/security", "b60205", "Seguridad (identidad/appsec)"),
    ("area/infra", "1d76db", "Infraestructura y despliegue"),
    ("area/backend", "0052cc", "Backend / datos"),
    ("area/observability", "fbca04", "Observabilidad"),
    ("area/governance", "5319e7", "Gobernanza / calidad / CI"),
    ("sev/high", "b60205", "Severidad alta"),
    ("sev/medium", "d93f0b", "Severidad media"),
    ("sev/low", "fef2c0", "Severidad baja"),
]

# code, título, area, body
EPICS = [
    ("E1", "Seguridad: Identidad y Acceso", "area/security",
     "Reducir privilegios por defecto y endurecer la gestión de sesiones. Specs: SPEC-001. ADR-0003."),
    ("E2", "Seguridad: Aplicación (AppSec)", "area/security",
     "Saneo de entradas no confiables y control de egress. Specs: SPEC-002. ADR-0003."),
    ("E3", "Infraestructura y Despliegue", "area/infra",
     "No exponer servicios internos, gestionar secretos, contenedores no-root. ADR-0003."),
    ("E4", "Datos y Persistencia", "area/backend",
     "Migraciones gestionadas (Alembic) y estado externalizable."),
    ("E5", "Observabilidad", "area/observability",
     "Logging estructurado, métricas, tracing y health checks. ADR-0004."),
    ("E6", "Gobernanza y Calidad (SDD)", "area/governance",
     "CI, cadena de suministro, auditoría y adopción de SDD. ADR-0002/0004."),
]

# título, area, sev, epic, body
TASKS = [
    ("T1.1 Rol seguro por defecto en el registro (SPEC-001)", "area/security", "sev/high", "E1",
     "register() asigna REDACTOR por defecto. Aplicar mínimo privilegio. Ver SPEC-001."),
    ("T1.2 Rate limiting + bloqueo de cuenta en login/register", "area/security", "sev/medium", "E1",
     "Sin protección contra fuerza bruta/credential stuffing."),
    ("T1.3 Revocación de JWT (jti store/blacklist) + refresh token", "area/security", "sev/medium", "E1",
     "jti se genera pero no se verifica; no hay logout server-side; login no emite refresh."),
    ("T1.4 Sacar el token JWT del query string del SSE", "area/security", "sev/high", "E1",
     "El stream usa ?token=...; fuga por logs/historial/proxy. Usar ticket de un solo uso o header."),
    ("T1.5 ENABLE_DEV_ROLE_PROMOTION default False + gate prod", "area/security", "sev/medium", "E1",
     "El merge YAML lo deja en True (config.py:116) pese al comentario MUST be False."),
    ("T1.6 Relegar seeds de credenciales débiles a flag de dev", "area/security", "sev/medium", "E1",
     "admin@admin/admin123, redactor123... se siembran en cada arranque SQLite."),
    ("T2.1 Protección SSRF en el scraper + quitar verify=False (SPEC-002)", "area/security", "sev/high", "E2",
     "_is_valid_url solo valida esquema/host; no bloquea loopback/privadas/metadata. Ver SPEC-002."),
    ("T2.2 Sanear URLs javascript:/data: en paper_layout + sandbox en iframe", "area/security", "sev/medium", "E2",
     "El conversor markdown->HTML no sanea enlaces y PaperViewPage usa iframe srcDoc sin sandbox."),
    ("T2.3 Validar subidas por magic bytes/content-type", "area/security", "sev/low", "E2",
     "Hoy solo allowlist de extensión + 10MB."),
    ("T2.4 Manejador global de excepciones (sin fugas de stack)", "area/security", "sev/medium", "E2",
     "Sin exception handler global; riesgo de fuga con DEBUG."),
    ("T3.1 Autenticar Qdrant (API key) y no exponer puertos internos", "area/infra", "sev/high", "E3",
     "Qdrant :6333 y Ollama :11434 expuestos sin auth; QDRANT_API_KEY None."),
    ("T3.2 Gestión de secretos fuera de git + rotación", "area/infra", "sev/high", "E3",
     "postgres/password, redis/password, minioadmin; SECRET_KEY commiteado pasa la validación."),
    ("T3.3 Contenedores no-root + imagen backend slim", "area/infra", "sev/medium", "E3",
     "Dockerfiles sin USER; build-essential en imagen final."),
    ("T3.4 Compose dev/prod separados; TLS; cabeceras + CSP en nginx", "area/infra", "sev/medium", "E3",
     "Compose mezcla --reload/DEBUG; nginx sin cabeceras de seguridad."),
    ("T3.5 Límites de recursos + healthchecks de readiness", "area/infra", "sev/low", "E3",
     "Ollama puede agotar RAM/VRAM; healthchecks parciales."),
    ("T4.1 Adoptar Alembic (reemplazar ALTER caseros)", "area/backend", "sev/medium", "E4",
     "init_db hace ALTER TABLE en try/except silencioso; Alembic está en requirements sin usar."),
    ("T4.2 Sacar dev.db de git + .gitignore", "area/backend", "sev/low", "E4",
     "SQLite binario trackeado."),
    ("T4.3 Externalizar estado en memoria a Redis (multi-worker)", "area/backend", "sev/medium", "E4",
     "active_streams/active_tasks/pending_decisions en memoria del proceso."),
    ("T5.1 Logging estructurado (JSON) + correlation IDs", "area/observability", "sev/medium", "E5",
     "Logs de texto con emojis, sin request_id."),
    ("T5.2 Métricas Prometheus (latencia, errores, tokens LLM)", "area/observability", "sev/medium", "E5",
     "Sin métricas más allá de agent_runs."),
    ("T5.3 Tracing OpenTelemetry (fase 2)", "area/observability", "sev/low", "E5",
     "Sin tracing distribuido."),
    ("T5.4 /health liveness/readiness con chequeo de dependencias", "area/observability", "sev/medium", "E5",
     "/health trivial; no comprueba DB/Qdrant/Ollama."),
    ("T6.1 CI en PRs: lint + pytest + build frontend", "area/governance", "sev/high", "E6",
     "No hay .github/workflows."),
    ("T6.2 Escaneo de dependencias (pip-audit/npm audit) + Dependabot", "area/governance", "sev/medium", "E6",
     "Sin escaneo de cadena de suministro."),
    ("T6.3 Pinear dependencias + lockfile/hashes", "area/governance", "sev/medium", "E6",
     "requirements con >=; sin hashes."),
    ("T6.4 Audit log de acciones sensibles", "area/governance", "sev/medium", "E6",
     "Sin auditoría de cambios de rol/publicación/accesos."),
    ("T6.5 Política de retención de datos y PII", "area/governance", "sev/low", "E6",
     "Sin retención ni tratamiento de PII."),
    ("T6.6 Adoptar SDD: specs, DoR/DoD, CODEOWNERS", "area/governance", "sev/medium", "E6",
     "Formalizado en la rama docs/sdd-governance."),
]

DOD = ("\n\n— Ver docs/backlog/security-hardening-backlog.md y la Definition of Done "
       "en docs/governance/GOVERNANCE.md.")


def gh(*args, check=True):
    res = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if check and res.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}\n{res.stderr.strip()}")
    return res.stdout


def gh_json(*args):
    return json.loads(gh(*args))


def node_id(issue_number):
    return gh("issue", "view", str(issue_number), "--repo", REPO, "--json", "id", "-q", ".id").strip()


def create_issue(title, body, labels):
    url = gh("issue", "create", "--repo", REPO, "--title", title, "--body", body,
             "--label", labels).strip().splitlines()[-1]
    number = int(re.search(r"/issues/(\d+)", url).group(1))
    return number, url


def main():
    print("==> Labels")
    for name, color, desc in LABELS:
        gh("label", "create", name, "--color", color, "--description", desc, "--force", "--repo", REPO)

    print("==> Project")
    existing = [p for p in gh_json("project", "list", "--owner", OWNER, "--format", "json")["projects"]
                if p.get("title") == PROJECT_TITLE]
    if existing and "--force" not in sys.argv:
        sys.exit(f"Ya existe un Project '{PROJECT_TITLE}' (#{existing[0]['number']}). "
                 "Bórralo con  python scripts/delete_github_project.py --yes  o reejecuta con --force.")
    proj = gh_json("project", "create", "--owner", OWNER, "--title", PROJECT_TITLE, "--format", "json")
    number, project_id = str(proj["number"]), proj["id"]
    print(f"    #{number} ({proj.get('url','')})")
    try:
        gh("project", "link", number, "--owner", OWNER, "--repo", REPO)
        print("    enlazado al repositorio")
    except RuntimeError as e:
        print(f"    aviso: no se pudo enlazar automáticamente ({e}). Usa 'Link a project' en la UI.")

    print("==> Campo Epic")
    gh("project", "field-create", number, "--owner", OWNER, "--name", FIELD_NAME,
       "--data-type", "SINGLE_SELECT", "--single-select-options",
       ",".join(c for c, *_ in EPICS))
    fields = gh_json("project", "field-list", number, "--owner", OWNER, "--format", "json")["fields"]
    field = next(f for f in fields if f.get("name") == FIELD_NAME)
    field_id = field["id"]
    opt = {o["name"]: o["id"] for o in field.get("options", [])}

    def add_and_tag(issue_url, epic_code):
        item = gh_json("project", "item-add", number, "--owner", OWNER, "--url", issue_url, "--format", "json")
        gh("project", "item-edit", "--id", item["id"], "--project-id", project_id,
           "--field-id", field_id, "--single-select-option-id", opt[epic_code])

    print("==> Épicas")
    epic_node = {}
    for code, title, area, body in EPICS:
        n, url = create_issue(f"[EPIC] {title}", body, f"epic,{area}")
        epic_node[code] = node_id(n)
        add_and_tag(url, code)
        print(f"    {code} -> #{n}")

    print("==> Tareas + sub-issues")
    for title, area, sev, code, body in TASKS:
        n, url = create_issue(title, body + DOD, f"task,{area},{sev}")
        add_and_tag(url, code)
        # Relación jerárquica nativa: la épica es la issue padre.
        try:
            gh("api", "graphql", "-f",
               "query=mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c}){subIssue{number}}}",
               "-f", f"p={epic_node[code]}", "-f", f"c={node_id(n)}")
        except RuntimeError as e:
            print(f"    aviso sub-issue {title[:30]}: {e}")
        print(f"    {code} ◂ #{n}")

    print(f"\nListo. Project: {proj.get('url','')}")
    print("En la UI:  View ▸ Group by ▸ Epic  (y activa 'sub-issues' en la tabla si quieres el árbol).")


if __name__ == "__main__":
    main()
