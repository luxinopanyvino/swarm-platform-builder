# Tarea #486 — Medición de AC3 con referencias reales de la revista

## 2026-10-22 — Éxito ✅ (parcial: la muestra real es mínima)

- **Rama:** `docs/medicion-ac3-muestra-revista`
- **PR:** la de esta rama → `develop` (`Closes #486`)
- **Origen:** pendiente de SPEC-032: «repetir la medición del AC3 con una muestra real de la revista».

### Qué se hizo y dónde

- Se extrajeron las referencias de los 5 artículos publicados de la base de desarrollo (sección *Referencias* y fuentes de los informes guardados) a
  `backend/evals/reference_resolution/journal-sample.jsonl` (`provenance: recorded`; mismo formato que el conjunto existente, así que el script lo mide con `--dataset`).
- Se midió con red real y se documentó en `docs/reports/medicion-ac3-muestra-revista.md`, con cuatro hallazgos (referencia solo con título publicada; un enlace
  de bienvenida como referencia; metadatos del RAG muy desiguales; autores incompletos sin «et al.»).
- Test: el conjunto nuevo se valida con la misma comprobación de formato que el anterior.

### Qué NO se hizo

- **No es una estimación de tasa**: 4 referencias distintas. La muestra suficiente y **revisada por la persona responsable** requiere el corpus real de la revista,
  que esta base de desarrollo no tiene.
- La **prueba manual** de `docs/qa/spec-032-verificacion-manual.md` es de interfaz y la hace una persona en el navegador.

### Definition of Done

- [x] Medición con red real y resultado documentado.
- [ ] Muestra revisada y suficiente (pendiente de la persona responsable).
- [ ] La CI de esta PR es la comprobación en Linux.
