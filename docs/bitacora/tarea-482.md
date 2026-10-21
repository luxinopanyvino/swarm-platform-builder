# Tarea #482 — DataCite como proveedor de los DOI de arXiv (DEC-1)

## 2026-10-22 — Éxito ✅

- **Rama:** `feat/compuerta-datacite-arxiv`
- **PR:** la de esta rama → `develop` (`Closes #482`)
- **Origen:** DEC-1 de `docs/reports/spec-032-decisiones-pendientes.md`, aprobada por la persona responsable. Los dos fallos con DOI de la medición real de AC3
  eran de arXiv: esos DOI los registra DataCite, Crossref responde 404 y OpenAlex dio un año equivocado y, en un caso, otra obra.

### Qué se hizo y dónde

- **`backend/app/platform/publication_gate/reference_resolver.py`:** proveedor `DataCite` (`_datacite_doi`, `_from_datacite`) para el prefijo `10.48550/`.
  Se consulta **primero** y es concluyente (un 404 es «no existe», sin preguntar a quien solo lo indexa); si no responde, cae a Crossref y OpenAlex y, como siempre,
  lo no comprobable es `not_verified`. Las reglas de coincidencia no cambian. La métrica de proveedor distingue `datacite`.
- **`backend/app/platform/egress.py`:** `api.datacite.org` en `HOSTS_COMPUERTA` (solo para la compuerta, no para la herramienta del modelo; los tests de despliegue
  recorren la lista, así que cubren el host nuevo).
- **Tests** (`test_gate_reference_existence.py`, 5 casos): resuelve en DataCite sin tocar Crossref; 404 concluyente; caída de DataCite → `not_verified`; los demás DOI no
  tocan DataCite; título/autores distintos siguen fallando.
- **Docs:** enmienda al final de ADR-0011; SPEC-032/AC16, `CLAUDE.md` y `data-retention.md` mencionan el host; actualización en el informe de medición;
  DEC-1 y DEC-2 resueltas en el informe de decisiones.

### Medición real (red, 2026-10-22)

`scripts/measure_reference_resolution.py`: **20/20 con DOI (100 %, antes 18/20)**, 10/12 sin DOI (sin cambios), **6/6 negativos bloqueados**. RESULTADO: CUMPLE, ahora con margen.

### Definition of Done

- [x] Tests nuevos y los de resolutor, despliegue y medición en verde.
- [x] Medición real repetida (arriba).
- [ ] La CI de esta PR es la comprobación en Linux.

### Notas

- Un host más en el camino crítico de publicar; documentado en la enmienda de ADR-0011.
- El conjunto de la medición sigue siendo escrito de memoria: falta repetirla con una muestra revisada de la revista.
