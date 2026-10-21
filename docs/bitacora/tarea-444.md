# Tarea #444 — T20.12 Publicador sin LLM, también en la traza

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-12-publicador-sin-llm`
- **PR:** la de esta rama → `develop` (`Closes #444`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC9 · épica E20 (#432)
- **Dependencias:** ninguna

### Dónde estaba el problema

El Publicador ya no llamaba al LLM (`adapters/publicador.py` solo escribe en BD y maqueta), pero la
traza de explicabilidad decía lo contrario: `use_cases.py` resolvía un modelo para **todos** los
agentes y lo guardaba en `agent_run_steps.model`, de modo que el panel «Por qué este resultado»
atribuía un modelo a un paso determinista (hallazgo de la matriz de la Fase 0).

### Qué se hizo y por qué

- `platform/engine/agents.py`: `uses_llm(name)` — un agente usa LLM si declara `llm` o `llm_stream`
  en `requires` (`template.yaml`). Un agente que el motor no conoce (los dinámicos de `.agent.md`)
  se considera con LLM: no se afirma «sin LLM» de algo no declarado.
- `application/use_cases.py`: el `model` del paso se resuelve solo si `uses_llm`; si no, `None`.
  La columna ya admitía nulo, así que no hay migración.
- No se tocó `publicador.py`: no había nada que quitar; lo que se añade es el test que impide que
  vuelva a aparecer.

### Definition of Done

- [x] **AC9** — el módulo no importa ni invoca `call_llm`/`call_llm_stream`/`resolve_agent_model`
  (comprobación por AST); la traza registra `model = null` para el Publicador y modelo para los demás.
- [x] Tests: `backend/tests/test_publicador_sin_llm.py` (8). Suite: 1127 pasados, los mismos 4 fallos
  que `develop`. Gate EDD sin regresión.

### Verificación

La traza se comprueba por la función `uses_llm` y por inspección del punto de uso en `use_cases.py`;
no se ejecutó un pipeline completo con base de datos para leer la fila resultante.

### Fuera de alcance / notas

- Las trazas ya guardadas conservan el modelo que se les atribuyó entonces; no se reescriben.
