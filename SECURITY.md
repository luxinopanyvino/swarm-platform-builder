# Política de seguridad

## Reporte de vulnerabilidades

Si encuentras una vulnerabilidad, **no abras un issue público**. Usa
*GitHub Security Advisories* (pestaña **Security → Report a vulnerability**) o
contacta de forma privada a los maintainers. Objetivo de respuesta inicial: 72 h.

## Alcance

Backend (FastAPI/LangGraph), frontend (React), e infraestructura de despliegue
(Docker Compose, Qdrant, Ollama, Postgres). Excluye dependencias de terceros
salvo cuando el proyecto las configura de forma insegura.

## Línea base de seguridad

Definida en [ADR-0003](docs/adr/0003-security-baseline-and-threat-model.md).
Marco objetivo: **OWASP ASVS L2** y **OWASP Top 10**. Resumen de controles
obligatorios:

- **Identidad:** mínimo privilegio en el registro; JWT con expiración corta y
  revocación; secretos fuertes validados al arranque; el token nunca viaja por URL.
- **AppSec:** saneo de entradas; egress con allowlist y bloqueo de
  loopback/rangos privados/metadata; TLS verificado; manejador global de errores.
- **Infra:** servicios internos no expuestos y autenticados; secretos fuera de
  git; contenedores no-root.
- **Cadena de suministro:** dependencias pineadas y escaneadas en CI.

## Modelo de amenazas (resumen)

| Activo | Amenaza | Mitigación |
|--------|---------|------------|
| Cuentas/roles | Escalada vía registro público | Rol mínimo por defecto (SPEC-001) |
| Red interna | SSRF desde el scraper | Allowlist + bloqueo de IP privadas (SPEC-002) |
| Vector DB / LLM | Acceso no autenticado | Auth + no exponer puertos (E3) |
| Tokens | Fuga por URL/logs | Token fuera de query; logging sin secretos |
| Secretos | Defaults/commiteados | Gestión de secretos + validación fail-fast |

El modelo completo se mantiene y revisa por release.

## Hallazgos abiertos

Los gaps detectados en la auditoría de junio 2026 están desglosados en
[`docs/backlog/security-hardening-backlog.md`](docs/backlog/security-hardening-backlog.md)
y volcados al GitHub Project del repositorio.
