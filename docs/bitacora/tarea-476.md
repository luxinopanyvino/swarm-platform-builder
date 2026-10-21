# Tarea #476 — Errores del Publicador visibles y aprobación sin carrera (DEC-6, DEC-7)

## 2026-10-22 — Éxito ✅

- **Rama:** `fix/compuerta-robustez`
- **PR:** la de esta rama → `develop` (`Closes #476`)
- **Origen:** dos hallazgos abiertos de SPEC-032 (`docs/reports/spec-032-decisiones-pendientes.md`, CHK030 y CHK031).

### Qué se hizo y dónde

- **DEC-6 · `adapters/publicador.py`:** el `except Exception` que envolvía la publicación y la compuerta se tragaba los fallos de base de datos y el
  pipeline seguía como si nada. Ahora registra el error en el log del paso (`error`) y **lo relanza**: el orquestador marca el paso `failed` y
  la persona lo ve y puede reanudar. No publica de más: el artículo conserva su estado.
- **DEC-7 · `routers/articles.py`:** `approve` y `publish` cargan el artículo con `SELECT … FOR UPDATE`. Dos aprobaciones simultáneas ya no leen
  `in_review` a la vez: la segunda espera, ve `published` y recibe 409. En `publish`, que hace un commit a mitad (guarda el informe
  reevaluado) y por eso suelta el bloqueo, se vuelve a tomar (`refresh(..., with_for_update=True)`) y se **recomprueba el estado** antes de decidir.
  SQLite ignora `FOR UPDATE`; en Postgres es lo que serializa.
- **Tests** (`tests/test_gate_robustness.py`, 3 casos): un fallo al guardar el informe sube, queda en el log del paso y no cambia el artículo;
  `approve` y `publish` toman el bloqueo; tras reevaluar se vuelve a bloquear antes de decidir. La serialización real depende de Postgres y no se
  puede ejercitar con SQLite: la prueba es estructural.
- **Doc:** DEC-6 y DEC-7 marcadas como resueltas en `spec-032-decisiones-pendientes.md`.

### Definition of Done

- [x] Tests nuevos y los de publicador, aprobación, `can_publish` y auditoría en verde (162).
- [ ] Verificación de la concurrencia real en Postgres: pendiente (no hay CI de carrera; los tests de integración con dos clientes son otra tarea).
- [ ] La CI de esta PR es la comprobación en Linux.
