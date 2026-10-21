# Tarea #434 — T20.2 Estructura de referencias, Formateador sin omisiones y Investigador que conserva metadatos

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-2-estructura-referencias`
- **PR:** la de esta rama → `develop` (`Closes #434`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC2 · épica E20 (#432)
- **Dependencias:** ninguna (T20.3 y T20.4 dependen de esta)

### Dónde estaba el problema

- `formateador.py` imprimía las fuentes con el campo vacío **omitido en silencio** (sin autores,
  año ni revista): el texto final parecía correcto aunque la referencia fuera un nombre de archivo.
- `investigador.py` fijaba `journal`, `year` y `doi` a `""` al construir cada fuente, pisando
  cualquier dato que el documento trajera, incluido un DOI aportado a mano.

### Qué se hizo y por qué

- `backend/app/platform/publication_gate/references.py` (nuevo): `check_reference_structure` y
  `missing_fields`. Una referencia es bloqueante si le falta identificador (DOI o URL http/https;
  las `local://` no cuentan), autores, año o publicación, y la evidencia dice cuál. Ignora la
  síntesis `synthesis://` del LLM. Valores como `N/A` cuentan como vacíos.
- `formateador.py`: ya no imprime fuentes incompletas; las deja fuera de la bibliografía, avisa por
  el log con lo que falta y devuelve `reference_issues` en el estado. Así nada se omite sin rastro y
  la compuerta (T20.4) puede bloquear con esa evidencia. Se añadió `reference_issues` a `AgentState`.
- `investigador.py`: `journal`, `year` y `doi` se toman del documento si existen, en vez de vaciarse.
- Orden de AC2: esta validación va **después** de resolver y enriquecer (T20.3); aquí solo se
  construye el validador.

### Definition of Done

- [x] **AC2** — referencia sin identificador, autores, año o publicación es bloqueante e indica el campo.
- [x] Tests: `backend/tests/test_gate_reference_structure.py` (8 casos) y los de formateador,
  paridad del motor y ACL siguen en verde.
- [ ] Interpretación de «el Formateador falla»: no se lanza excepción (con el RAG actual casi toda
  fuente es incompleta y el pipeline no terminaría nunca); se excluye y se informa. Si se quiere
  el fallo literal, decidirlo en T20.4 con la compuerta ya conectada.

### Verificación

Suite completa sin `test_tracing.py` (falta `opentelemetry` en este entorno): 1104 passed,
4 failed (`test_frontend_layers` ×2, `test_no_tracked_databases`, `test_la_spec_de_finetune_sigue_en_draft`),
ninguno relacionado con este cambio; SPEC-032 AC12 cuenta 4 fallos preexistentes en `develop`.
No se ejecutó el pipeline completo con un LLM real.

### Fuera de alcance / notas

- Un manuscrito **sin ninguna referencia** pasa esta comprobación (CHK034 sigue abierto).
- Sin evaluación EDD en esta PR: no cambia prompts ni el comportamiento medido del agente; la
  actualización de datasets es T20.15.
