# Tarea #484 — Despliegue gradual de la compuerta en modo aviso y reporte de medición (DEC-4)

## 2026-10-22 — Éxito ✅

- **Rama:** `feat/compuerta-despliegue-gradual`
- **PR:** la de esta rama → `develop` (`Closes #484`)
- **Origen:** DEC-4, aprobada por la persona responsable. Con `PUBLICATION_GATE_ENFORCE=true` casi nada pasa hoy (las fuentes del RAG no traen DOI):
  se despliega en modo aviso, se mide y se activa cuando los bloqueantes sean accionables. La entrada de interfaz para aportar el DOI a mano ya está en #472.

### Qué se hizo y dónde

- **`config.yaml` y `backend/config.yaml`:** `publication.gate_enforce: false` (modo aviso). **El valor por defecto del código sigue siendo `true`**: un entorno sin
  configuración falla cerrado. La aprobación humana, el autor responsable y la revisión ≥ 80 siguen siendo obligatorios en los dos modos.
- **`scripts/gate_rollout_report.py`:** solo lee los informes (el último de cada artículo en una ventana) y dice cuántos pasarían, cuántos se bloquean por un solo
  criterio y qué criterios bloquean más; recomienda activar con ≥ 20 manuscritos y ≥ 80 % (ajustable). Es una recomendación, no un interruptor.
- **`docs/governance/publication-gate-rollout.md`:** el procedimiento (desplegar, medir, atacar lo que más bloquea, activar por PR, vigilar, volver atrás).
- **Tests:** `test_gate_rollout_report.py` (5 casos: conteo, muestra pequeña, umbrales, sin informes, solo lectura) y `test_gate_deployment.py` ajustado: el
  default del código es `true` y el valor efectivo es el del yaml (las dos copias deben coincidir).

### Definition of Done

- [x] Tests nuevos y los de despliegue en verde.
- [ ] Medir en el entorno real tras 1–2 semanas y decidir la activación (fuera de esta tarea: es el procedimiento).
- [ ] La CI de esta PR es la comprobación en Linux.
