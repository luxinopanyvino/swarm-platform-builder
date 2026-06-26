#!/usr/bin/env bash
#
# Vuelca el backlog de hardening (docs/backlog/security-hardening-backlog.md)
# al GitHub Project del repositorio: crea labels, un Project v2, e issues de
# épicas y tareas (las tareas referencian a su épica).
#
# Requisitos:
#   - gh CLI autenticado:  gh auth login   (scopes: repo, project, read:org)
#   - Ejecutar desde la raíz del repo.
#
# Uso:
#   bash scripts/seed-github-project.sh
#
# Variables (override por entorno):
#   OWNER, REPO, PROJECT_TITLE
set -euo pipefail

OWNER="${OWNER:-luxinopanyvino}"
REPO="${REPO:-luxinopanyvino/swarm-platform-builder}"
PROJECT_TITLE="${PROJECT_TITLE:-Hardening & Platform Backlog}"

command -v gh >/dev/null || { echo "ERROR: instala gh CLI"; exit 1; }
gh auth status >/dev/null 2>&1 || { echo "ERROR: ejecuta 'gh auth login' (scopes: repo, project)"; exit 1; }

echo "==> Creando labels"
label() { gh label create "$1" --color "$2" --description "$3" --force --repo "$REPO" >/dev/null; }
label "epic"               "5319e7" "Épica del backlog"
label "task"               "0e8a16" "Tarea de implementación"
label "area/security"      "b60205" "Seguridad (identidad/appsec)"
label "area/infra"         "1d76db" "Infraestructura y despliegue"
label "area/backend"       "0052cc" "Backend / datos"
label "area/observability" "fbca04" "Observabilidad"
label "area/governance"    "5319e7" "Gobernanza / calidad / CI"
label "sev/high"           "b60205" "Severidad alta"
label "sev/medium"         "d93f0b" "Severidad media"
label "sev/low"            "fef2c0" "Severidad baja"

echo "==> Creando Project v2: $PROJECT_TITLE"
PROJECT_NUMBER="$(gh project create --owner "$OWNER" --title "$PROJECT_TITLE" --format json \
  | grep -oE '"number":[0-9]+' | head -1 | grep -oE '[0-9]+')"
echo "    Project #$PROJECT_NUMBER"

add_to_project() { gh project item-add "$PROJECT_NUMBER" --owner "$OWNER" --url "$1" >/dev/null; }
issue_url() { gh issue create --repo "$REPO" --title "$1" --body "$2" --label "$3" | tail -1; }

declare -A EPIC_URL
declare -A EPIC_NUM

create_epic() { # id  title  area  body
  local url; url="$(issue_url "[EPIC] $2" "$4" "epic,$3")"
  EPIC_URL[$1]="$url"; EPIC_NUM[$1]="$(echo "$url" | grep -oE '[0-9]+$')"
  add_to_project "$url"; echo "    EPIC $1 -> $url"
}

create_task() { # title  area  sev  epic_id  body
  local body="$5

— Parte de la épica **$4** (#${EPIC_NUM[$4]}). Ver docs/backlog/security-hardening-backlog.md y la Definition of Done en docs/governance/GOVERNANCE.md."
  local url; url="$(issue_url "$1" "$body" "task,$2,$3")"
  add_to_project "$url"; echo "      task -> $url"
}

echo "==> Creando épicas"
create_epic E1 "Seguridad: Identidad y Acceso" "area/security" \
  "Reducir privilegios por defecto y endurecer la gestión de sesiones. Specs: SPEC-001. ADR-0003."
create_epic E2 "Seguridad: Aplicación (AppSec)" "area/security" \
  "Saneo de entradas no confiables y control de egress. Specs: SPEC-002. ADR-0003."
create_epic E3 "Infraestructura y Despliegue" "area/infra" \
  "No exponer servicios internos, gestionar secretos, contenedores no-root. ADR-0003."
create_epic E4 "Datos y Persistencia" "area/backend" \
  "Migraciones gestionadas (Alembic) y estado externalizable."
create_epic E5 "Observabilidad" "area/observability" \
  "Logging estructurado, métricas, tracing y health checks. ADR-0004."
create_epic E6 "Gobernanza y Calidad (SDD)" "area/governance" \
  "CI, cadena de suministro, auditoría y adopción de SDD. ADR-0002/0004."

echo "==> Creando tareas"
# E1
create_task "T1.1 Rol seguro por defecto en el registro (SPEC-001)" area/security sev/high E1 \
  "register() asigna REDACTOR por defecto. Aplicar mínimo privilegio. Ver SPEC-001."
create_task "T1.2 Rate limiting + bloqueo de cuenta en login/register" area/security sev/medium E1 \
  "Sin protección contra fuerza bruta/credential stuffing."
create_task "T1.3 Revocación de JWT (jti store/blacklist) + refresh token" area/security sev/medium E1 \
  "jti se genera pero no se verifica; no hay logout server-side; login no emite refresh."
create_task "T1.4 Sacar el token JWT del query string del SSE" area/security sev/high E1 \
  "El stream usa ?token=...; fuga por logs/historial/proxy. Usar ticket de un solo uso o header."
create_task "T1.5 ENABLE_DEV_ROLE_PROMOTION default False + gate prod" area/security sev/medium E1 \
  "El merge YAML lo deja en True (config.py:116) pese al comentario MUST be False."
create_task "T1.6 Relegar seeds de credenciales débiles a flag de dev" area/security sev/medium E1 \
  "admin@admin/admin123, redactor123… se siembran en cada arranque SQLite."
# E2
create_task "T2.1 Protección SSRF en el scraper + quitar verify=False (SPEC-002)" area/security sev/high E2 \
  "_is_valid_url solo valida esquema/host; no bloquea loopback/privadas/metadata. Ver SPEC-002."
create_task "T2.2 Sanear URLs javascript:/data: en paper_layout + sandbox en iframe" area/security sev/medium E2 \
  "El conversor markdown→HTML no sanea enlaces y PaperViewPage usa iframe srcDoc sin sandbox."
create_task "T2.3 Validar subidas por magic bytes/content-type" area/security sev/low E2 \
  "Hoy solo allowlist de extensión + 10MB."
create_task "T2.4 Manejador global de excepciones (sin fugas de stack)" area/security sev/medium E2 \
  "Sin exception handler global; riesgo de fuga con DEBUG."
# E3
create_task "T3.1 Autenticar Qdrant (API key) y no exponer puertos internos" area/infra sev/high E3 \
  "Qdrant :6333 y Ollama :11434 expuestos sin auth; QDRANT_API_KEY None."
create_task "T3.2 Gestión de secretos fuera de git + rotación" area/infra sev/high E3 \
  "postgres/password, redis/password, minioadmin; SECRET_KEY commiteado pasa la validación."
create_task "T3.3 Contenedores no-root + imagen backend slim" area/infra sev/medium E3 \
  "Dockerfiles sin USER; build-essential en imagen final."
create_task "T3.4 Compose dev/prod separados; TLS; cabeceras + CSP en nginx" area/infra sev/medium E3 \
  "Compose mezcla --reload/DEBUG; nginx sin cabeceras de seguridad."
create_task "T3.5 Límites de recursos + healthchecks de readiness" area/infra sev/low E3 \
  "Ollama puede agotar RAM/VRAM; healthchecks parciales."
# E4
create_task "T4.1 Adoptar Alembic (reemplazar ALTER caseros)" area/backend sev/medium E4 \
  "init_db hace ALTER TABLE en try/except silencioso; Alembic está en requirements sin usar."
create_task "T4.2 Sacar dev.db de git + .gitignore" area/backend sev/low E4 \
  "SQLite binario trackeado."
create_task "T4.3 Externalizar estado en memoria a Redis (multi-worker)" area/backend sev/medium E4 \
  "active_streams/active_tasks/pending_decisions en memoria del proceso."
# E5
create_task "T5.1 Logging estructurado (JSON) + correlation IDs" area/observability sev/medium E5 \
  "Logs de texto con emojis, sin request_id."
create_task "T5.2 Métricas Prometheus (latencia, errores, tokens LLM)" area/observability sev/medium E5 \
  "Sin métricas más allá de agent_runs."
create_task "T5.3 Tracing OpenTelemetry (fase 2)" area/observability sev/low E5 \
  "Sin tracing distribuido."
create_task "T5.4 /health liveness/readiness con chequeo de dependencias" area/observability sev/medium E5 \
  "/health trivial; no comprueba DB/Qdrant/Ollama."
# E6
create_task "T6.1 CI en PRs: lint + pytest + build frontend" area/governance sev/high E6 \
  "No hay .github/workflows."
create_task "T6.2 Escaneo de dependencias (pip-audit/npm audit) + Dependabot" area/governance sev/medium E6 \
  "Sin escaneo de cadena de suministro."
create_task "T6.3 Pinear dependencias + lockfile/hashes" area/governance sev/medium E6 \
  "requirements con >=; sin hashes."
create_task "T6.4 Audit log de acciones sensibles" area/governance sev/medium E6 \
  "Sin auditoría de cambios de rol/publicación/accesos."
create_task "T6.5 Política de retención de datos y PII" area/governance sev/low E6 \
  "Sin retención ni tratamiento de PII."
create_task "T6.6 Adoptar SDD: specs, DoR/DoD, CODEOWNERS" area/governance sev/medium E6 \
  "Formalizado en esta rama docs/sdd-governance."

echo "==> Hecho. Project: https://github.com/users/$OWNER/projects/$PROJECT_NUMBER"
