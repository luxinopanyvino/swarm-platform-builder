# SPEC-016: AppSec — saneamiento de salida, subidas y errores (E2 resto)

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E2 (Seguridad: Aplicación / AppSec)
- **ADR relacionado:** ADR-0003
- **Severidad:** 🟠

> Adopta formalmente las tareas T2.2–T2.4 sembradas por el bootstrap sin spec.
> T2.1 (SSRF del scraper) pertenece a [SPEC-002](SPEC-002-scraper-ssrf-protection.md),
> hoy **Superseded** porque el scraper se eliminó (`71e3923`); no se reactiva aquí.

## 1. Problema

Tres huecos AppSec sin relación con el scraper eliminado:
el conversor markdown→HTML de `paper_layout` no sanea enlaces
`javascript:`/`data:` y `PaperViewPage` renderiza con `iframe srcDoc` sin
`sandbox` (XSS almacenado); las subidas al RAG solo validan extensión y tamaño
(10 MB), no contenido; y no existe manejador global de excepciones, con riesgo
de fuga de stack traces en `500`.

## 2. Objetivos / No-objetivos

- **Objetivos:** neutralizar XSS en el HTML generado, validar subidas por
  contenido real, y errores `500` opacos y trazables.
- **No-objetivos:** CSP de nginx (T3.4, SPEC-017); antivirus/escaneo de malware
  de ficheros.

## 3. Criterios de aceptación

- [ ] **AC1** — *Given* markdown con enlaces `javascript:` o `data:`, *When*
  `paper_layout` lo convierte a HTML, *Then* esos esquemas quedan eliminados o
  neutralizados, y el iframe de `PaperViewPage` lleva `sandbox` sin
  `allow-same-origin`+`allow-scripts` simultáneos.
- [ ] **AC2** — *Given* una subida cuyo contenido (magic bytes) no corresponde
  a su extensión/`content-type` declarado, *When* se procesa, *Then* se rechaza
  con `400` **antes** de extraer texto o indexar.
- [ ] **AC3** — *Given* una excepción no controlada, *When* `DEBUG=false`,
  *Then* la respuesta `500` no expone stack trace ni detalles internos, y el
  error queda logueado con identificador de correlación.
- [ ] **AC4** — Existen tests que cubren AC1–AC3 con casos representativos.

## 4. Diseño propuesto

AC1: sanear en el conversor (allowlist de esquemas `http/https/mailto` +
atributo `sandbox` en el iframe). AC2: validación por magic bytes en el upload
del RAG (`pypdf`/firmas conocidas) previa a `extract_text`. AC3:
`app.add_exception_handler(Exception, …)` en `backend/app/main.py` con respuesta
genérica + log estructurado (se integra con T5.1 cuando exista).

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Falsos positivos de magic bytes en formatos raros | Bajo | Allowlist explícita de tipos soportados |
| Sandbox rompe estilos del paper | Bajo | `allow-same-origin` solo si no hay scripts |

## 6. Plan de pruebas

Unit del sanitizador (payloads `javascript:`, `data:text/html`), unit del
validador de magic bytes (PDF válido, PDF renombrado, HTML disfrazado), e2e del
handler global (`500` sin traza con `DEBUG=false`).

## 7. Impacto operativo / observabilidad

Contador/log de subidas rechazadas y de errores 500 correlacionados.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E2
  title: "Seguridad: Aplicación (AppSec)"
  area: area/security
tasks:
  - id: T2.2
    title: "Sanear URLs javascript:/data: en paper_layout + sandbox en iframe"
    sev: medium
    depends_on: []
    acceptance: [AC1, AC4]
  - id: T2.3
    title: Validar subidas por magic bytes/content-type
    sev: low
    depends_on: []
    acceptance: [AC2, AC4]
  - id: T2.4
    title: Manejador global de excepciones (sin fugas de stack)
    sev: medium
    depends_on: []
    acceptance: [AC3, AC4]
```
