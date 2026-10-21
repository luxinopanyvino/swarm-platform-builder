# Tarea #478 — Borrar el dominio muerto `modules/articles` (DEC-5)

## 2026-10-22 — Éxito ✅

- **Rama:** `chore/borrar-modules-articles`
- **PR:** la de esta rama → `develop` (`Closes #478`)
- **Origen:** DEC-5 de `docs/reports/spec-032-decisiones-pendientes.md`.

### Qué se hizo y dónde

- Se borra `backend/app/modules/articles/` (adaptadores, aplicación y dominio hexagonales). Tenía su propio `ArticleStatus` y un `publish()` que no pasaba
  por la compuerta; nadie lo importaba (solo se referenciaba a sí mismo) y declaraba un `ArticleORM` sobre la tabla `articles` en paralelo al modelo real.
- `tests/test_can_publish.py`: el test que vigilaba que siguiera sin usarse pasa a comprobar que **no reaparece** (ni el directorio ni importaciones
  de `app.modules.articles`), y la exclusión del dominio huérfano en el test de «nada asigna `published`» queda sin efecto.
- `docs/reports/spec-032-decisiones-pendientes.md`: DEC-5 resuelta.

### Definition of Done

- [x] Sin referencias restantes en `backend/` (la búsqueda solo encuentra la propia comprobación y bitácoras históricas).
- [x] Suite completa sin regresiones (ver PR).
- [ ] La CI de esta PR es la comprobación en Linux.
