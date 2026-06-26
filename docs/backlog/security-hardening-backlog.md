# Backlog de hardening y plataforma

Épicas y tareas derivadas de la auditoría transversal (junio 2026). Mapea los 6
ejes: **Seguridad (Identidad y AppSec), Infra, Datos, Observabilidad,
Gobernanza**. Severidad: 🔴 alto · 🟠 medio · 🟡 bajo.

Estas tareas se vuelcan al **GitHub Project** con
[`scripts/seed_github_project.py`](../../scripts/seed_github_project.py) (atómico
y jerárquico: crea el campo `Epic`, enlaza el proyecto al repo y crea relaciones
sub-issue épica→tareas). Para limpiar todo:
[`scripts/delete_github_project.py`](../../scripts/delete_github_project.py).
Labels: `epic`, `task`, `area/*`, `sev/{high,medium,low}`.

---

## E1 — Seguridad: Identidad y Acceso  · `area/security`
> Reducir privilegios por defecto y endurecer la gestión de sesiones.

| ID | Tarea | Sev |
|----|-------|-----|
| T1.1 | Rol seguro por defecto en el registro (SPEC-001) | 🔴 |
| T1.2 | Rate limiting + bloqueo de cuenta en login/register | 🟠 |
| T1.3 | Revocación de JWT (almacén de `jti`/blacklist) y emisión de refresh token | 🟠 |
| T1.4 | Sacar el token JWT del *query string* del SSE (ticket de un solo uso / header) | 🔴 |
| T1.5 | `ENABLE_DEV_ROLE_PROMOTION` default `False` y gate de producción | 🟠 |
| T1.6 | Relegar seeds de credenciales débiles a un flag de dev explícito | 🟠 |

## E2 — Seguridad: Aplicación (AppSec)  · `area/security`
> Saneo de entradas no confiables y control de egress.

| ID | Tarea | Sev |
|----|-------|-----|
| T2.1 | Protección SSRF en el scraper + quitar `verify=False` (SPEC-002) | 🔴 |
| T2.2 | Sanear URLs `javascript:`/`data:` en `paper_layout` y añadir `sandbox` al iframe | 🟠 |
| T2.3 | Validar subidas por *magic bytes*/content-type (no solo extensión) | 🟡 |
| T2.4 | Manejador global de excepciones (sin fugas de stack en 500) | 🟠 |

## E3 — Infraestructura y Despliegue  · `area/infra`
> No exponer servicios internos, gestionar secretos, contenedores no-root.

| ID | Tarea | Sev |
|----|-------|-----|
| T3.1 | Autenticar Qdrant (API key) y no publicar puertos internos al host | 🔴 |
| T3.2 | Gestión de secretos (Docker secrets/.env fuera de git) + rotación | 🔴 |
| T3.3 | Contenedores no-root + imagen backend slim (multi-stage, sin build-essential) | 🟠 |
| T3.4 | Separar compose dev/prod; TLS/HTTPS; cabeceras de seguridad + CSP en nginx | 🟠 |
| T3.5 | Límites de recursos + healthchecks de readiness por servicio | 🟡 |

## E4 — Datos y Persistencia  · `area/backend`
> Migraciones gestionadas y estado externalizable.

| ID | Tarea | Sev |
|----|-------|-----|
| T4.1 | Adoptar Alembic (reemplazar los `ALTER TABLE` caseros de `init_db`) | 🟠 |
| T4.2 | Sacar `backend/data/dev.db` de git y añadir a `.gitignore` | 🟡 |
| T4.3 | Externalizar estado en memoria (streams/tasks/decisiones) a Redis para multi-worker | 🟠 |

## E5 — Observabilidad  · `area/observability`
> Visibilidad de salud, rendimiento y uso de LLM.

| ID | Tarea | Sev |
|----|-------|-----|
| T5.1 | Logging estructurado (JSON) + `request_id`/correlation IDs | 🟠 |
| T5.2 | Métricas Prometheus (latencia, errores, duración de pipeline, tokens LLM) | 🟠 |
| T5.3 | Tracing OpenTelemetry (fase 2) | 🟡 |
| T5.4 | `/health` con liveness/readiness y chequeo de dependencias (DB/Qdrant/Ollama) | 🟠 |

## E6 — Gobernanza y Calidad (SDD)  · `area/governance`
> CI, cadena de suministro, auditoría y adopción de SDD.

| ID | Tarea | Sev |
|----|-------|-----|
| T6.1 | CI en PRs: lint + `pytest` + build frontend | 🔴 |
| T6.2 | Escaneo de dependencias (`pip-audit`/`npm audit`) + Dependabot | 🟠 |
| T6.3 | Pinear dependencias + lockfile/hashes (builds reproducibles) | 🟠 |
| T6.4 | Audit log de acciones sensibles (cambios de rol, publicación, accesos) | 🟠 |
| T6.5 | Política de retención de datos y tratamiento de PII | 🟡 |
| T6.6 | Adoptar SDD: plantillas de spec, DoR/DoD, CODEOWNERS (este PR) | 🟠 |

---

### Orden recomendado de ejecución

1. **🔴 primero:** T1.1, T1.4, T2.1, T3.1, T3.2, T6.1.
2. **🟠 baratos:** T1.5, T2.2, T2.4, T4.2, T5.4, T6.2.
3. Resto de 🟠 y 🟡 por capacidad.

Criterio de cierre de cada tarea: cumplir su Definition of Done
([GOVERNANCE §6](../governance/GOVERNANCE.md)).
