# Tarea #383 — T13.2 Ejecutar el benchmark y producir el informe comparativo

## 2026-09-15 — Completada ✅ (verificación de trabajo previo)

- **Rama:** `docs/cerrar-t13-1-t13-2`
- **PR:** la de esta rama → `develop` (`Closes #383`)
- **Spec/ADR:** [SPEC-025](../specs/SPEC-025-model-benchmark-scientific-writing.md) (AC1)
- **Dependencias:** #382 (T13.1), que se cierra en la misma PR

### Qué se hizo

El benchmark se ejecutó el 2026-08-09 (commit `d70c67f`) y su informe está versionado
en [`docs/reports/model-benchmark-scientific-writing.md`](../reports/model-benchmark-scientific-writing.md).
Esta entrada **no añade código**: verifica el informe y cierra la tarea por el flujo.

- **8 candidatos:** `llama3.2:1b`, `gemma2:2b`, `qwen2.5:3b`, `llama3.2:3b`,
  `mistral:7b`, `llama3:8b`, `llama3-chatqa:latest` y `llama3-chatqa:70b`, este último
  documentado como no viable en el hardware de la corrida.
- **Por modelo y rol:** score de calidad, latencia, palabras por segundo y RAM/VRAM.
- **Hardware declarado:** i5-1035G1, 12 GB de RAM, sin GPU dedicada.
- **Limitaciones escritas antes de las tablas:** una sola muestra por celda, una celda
  contaminada por una suspensión del equipo y corregida, y la métrica de citas APA en 0
  para todos los modelos.

### Definition of Done

- [x] **AC1** (informe comparativo versionado con métricas de razonamiento/calidad y de
  cómputo por modelo y por rol): presente en `docs/reports/`, con resumen por modelo y
  tablas por rol.

### Verificación

- Lectura del informe: cabecera generada por `run_benchmark.py`, tabla resumen con los
  8 modelos y secciones por rol (investigador, redactor, revisor, formateador).

### Fuera de alcance / notas

- La **selección** de modelos del informe es un borrador pendiente de ratificar: es
  T13.3 (#384), que sigue abierta. Antes pide repetir la prueba del revisor y revisar a
  mano salidas del formateador.
- Las cifras de latencia son de un portátil sin GPU. En la RTX 3070 Ti del equipo actual
  serían distintas; conviene tenerlo en cuenta en T13.3.
