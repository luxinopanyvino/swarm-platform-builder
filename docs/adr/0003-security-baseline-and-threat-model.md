# ADR-0003: Línea base de seguridad y modelo de amenazas

- **Estado:** Propuesto
- **Fecha:** 2026-06-26
- **Decisores:** Equipo de plataforma, Seguridad
- **Specs relacionadas:** SPEC-001 (registro/RBAC), SPEC-002 (SSRF)

## Contexto

La auditoría transversal (junio 2026) identificó gaps 🔴/🟠 en identidad,
AppSec e infraestructura, entre ellos:

- registro público que otorga rol `REDACTOR` (acceso a pipelines, subida de
  ficheros y scraper),
- scraper sin protección **SSRF** y con verificación TLS desactivada,
- Qdrant/Ollama expuestos sin autenticación,
- token JWT transmitido por *query string* en el stream SSE,
- secretos por defecto/commiteados.

No existe un modelo de amenazas ni una línea base de seguridad acordada.

## Decisión

Adoptaremos una **línea base de seguridad** mínima obligatoria y un **modelo de
amenazas** mantenido en `SECURITY.md`:

1. **Identidad:** rol por defecto de mínimo privilegio en el registro; JWT con
   expiración corta y mecanismo de revocación; secretos fuertes validados al
   arranque (fail-fast). El token nunca viaja por URL.
2. **AppSec:** validación/saneo de entradas no confiables; egress controlado
   (allowlist + bloqueo de rangos privados/metadata) para cualquier fetch
   saliente; TLS verificado; manejador global de errores sin fugas.
3. **Infra:** servicios internos (DB, Qdrant, Ollama, Redis) **no** expuestos
   públicamente y autenticados; secretos gestionados fuera de git; contenedores
   no-root.
4. **Proceso:** cada PR pasa escaneo de dependencias; los cambios sensibles
   requieren revisión de CODEOWNERS de seguridad; las amenazas se revisan por
   release.

Marco de referencia: **OWASP ASVS** (nivel 2 como objetivo) y **OWASP Top 10**.

## Alternativas consideradas

- **Pentest puntual sin línea base** — detecta pero no previene la regresión.
- **Hardening ad-hoc** — sin criterios, inconsistente entre PRs.

## Consecuencias

- **Positivas:** criterios de seguridad verificables y repetibles; base para el
  backlog de hardening (épicas E1–E3).
- **Negativas / coste:** fricción adicional en PRs; trabajo de remediación.
- **Seguimiento:** SPEC-001 y SPEC-002 detallan las dos primeras remediaciones;
  el resto se desglosa en `docs/backlog/security-hardening-backlog.md`.
