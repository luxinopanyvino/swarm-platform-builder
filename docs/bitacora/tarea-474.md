# Tarea #474 — follow-redirects 1.16.1 (npm audit en rojo en develop)

## 2026-10-22 — Éxito ✅

- **Rama:** `sec/follow-redirects-1-16-1`
- **PR:** la de esta rama → `develop` (`Closes #474`)
- **Origen:** #465 (#464) se fusionó con su primer commit; el arreglo de `follow-redirects` llegó después a la rama y no entró en `develop`.
  El job «Cadena de suministro» seguía fallando en `npm audit --omit=dev --audit-level=high` (1 aviso alto, `GHSA-q3jh-wrc6-jgq8` y `GHSA-8r9p-f939-6h3c`).

### Qué se hizo y dónde

- `frontend/package-lock.json`: `follow-redirects` 1.16.0 → **1.16.1** (3 líneas; dependencia transitiva, sin salto de versión mayor). Es el mismo
  cambio que se había comprobado en #464 (`npm audit` sale con 0; ambos builds de Vite pasan).

### Definition of Done

- [x] `npm audit --omit=dev --audit-level=high` → 0 (comprobado en #464 con este mismo lock).
- [ ] La CI de esta PR es la comprobación: el job de auditoría debe pasar.

### Notas

- Los dos avisos moderados de `react-router` siguen (necesitan un salto mayor); el job solo bloquea en `high`.
