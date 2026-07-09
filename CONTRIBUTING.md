# Guía de contribución

Este proyecto sigue **Spec-Driven Development (SDD)**
([ADR-0002](docs/adr/0002-adopt-spec-driven-development.md)). Lee también
[GOVERNANCE.md](docs/governance/GOVERNANCE.md) y [SECURITY.md](SECURITY.md).

## Flujo de trabajo (SDD)

```
Idea ─▶ Spec (docs/specs) ─▶ ADR si hay decisión arquitectónica
     ─▶ Épica + Tareas (GitHub Project) ─▶ Rama feat/… ─▶ PR contra develop
     ─▶ CI verde + revisión ─▶ Verificación contra criterios de aceptación ─▶ Merge
```

1. **Spec primero** para features/épicas significativas: copia
   `docs/specs/TEMPLATE.md` a `docs/specs/SPEC-NNN-...md`. Debe cumplir la
   **Definition of Ready** ([GOVERNANCE §5](docs/governance/GOVERNANCE.md)).
2. **ADR** si la spec implica una decisión arquitectónica (auth, almacenamiento,
   despliegue, etc.).
3. **Desglosa** en épica + tareas en el GitHub Project (labels `area/*`, `sev/*`).
4. **Implementa** en una rama `feat/…` (nunca en `develop`).
5. **PR contra `develop`** referenciando la spec/issue. No se mergea hasta cumplir
   la **Definition of Done** ([GOVERNANCE §6](docs/governance/GOVERNANCE.md)).

## Estándares de código

- **Backend:** Python 3.12, FastAPI, SQLAlchemy async. Tests con `pytest`
  (`backend/tests`). Sin secretos en el código.
- **Frontend:** React + Vite. `npm run build` debe pasar. Referencias a archivos
  como enlaces relativos en docs.
- **Commits:** convencionales (`feat:`, `fix:`, `docs:`, `sec:`, `chore:`).

## Antes de abrir el PR

- [ ] `pytest` en verde (backend) y `npm run build` (frontend).
- [ ] Sin secretos ni PII en el diff ni en logs.
- [ ] Spec/ADR/documentación actualizados.
- [ ] Criterios de aceptación de la spec verificados.

## Desarrollo local

Usa `dev-local.cmd` (Windows): backend `uvicorn --reload` en `:8000` (SQLite) y
frontend Vite en `:5173`. No confundir con el despliegue Docker (`:8080`).
