# Matriz de implementación — Fase 0 del plan de mejoras del pipeline

- **Fecha:** 2026-10-21
- **Base:** `develop` en `1fb850e` (más #426 aún sin mergear, no relevante aquí)
- **Alcance:** diagnóstico **solo de lectura** del backend (tareas 0.2 a 0.7 del plan). No se ha cambiado código.
- **Origen:** informe «Framework vs. plataforma actual» (PR-FW-001, 20/10/2026) y plan de implementación de mejoras.

## Limitaciones de este documento (leer antes de las tablas)

1. **Falta la tarea 0.1.** Los artefactos de PR-FW-001 (salidas intermedias, texto antes/después del Formateador, logs) no están en el repositorio. Sin ellos, aquí se afirma lo que **dice el código**, no lo que ocurrió en esa ejecución. Hay que aportarlos.
2. **Los criterios V01–V16 no están definidos en el repo.** El plan solo nombra algunos (V01, V05, V07, V09, V10, V12–V14, V16). Los demás (V02, V03, V04, V06, V08, V11, V15) figuran como «definición pendiente» en lugar de adivinarlos. Hace falta el texto del Framework v0.1.
3. Solo se leyó código; no se ejecutó el pipeline.

Leyenda de estado: **implementado** · **parcial** · **ausente**.

---

## 1. Hallazgos del diagnóstico (respuestas a 0.2–0.6)

### 0.2 Mapa de los agentes revisados

| Agente | Archivo | Qué hace realmente |
|---|---|---|
| Revisor | `backend/app/modules/agents/adapters/revisor.py`, `run_revisor` | Un solo prompt al LLM que pide `{approval_score, coherent, feedback[]}`. Sin desglose por criterio. |
| Formateador | `…/adapters/formateador.py`, `run_formateador` | Un LLM **reescribe el manuscrito entero** para el estilo de cita en texto; la bibliografía se arma en Python con `format_source_deterministic`. |
| Publicador | `…/adapters/publicador.py`, `run_publicador` | Escribe el texto en BD, marca `PUBLISHED`, genera `paper_html`. Sin validación de ningún tipo. |

### 0.3 Contrato real entre agentes

- Todos comparten **un único `AgentState`** (`modules/agents/domain/entities.py`); no hay esquemas por agente. Cada nodo recibe el estado completo.
- `feedback` es un canal acumulativo (`Annotated[List[str], operator.add]`): los comentarios de todas las vueltas se suman.
- **El Formateador y el Publicador no leen `feedback`** en su código ni en el prompt del Formateador. Reciben los comentarios solo en el sentido de que están en el estado compartido, y `agent_end` los emite en el `output` del Revisor. Quién los ve «llegar» a esos agentes en el informe debe confirmarse con los artefactos de 0.1 (traza `input_digest` en `agent_run_steps`). Hay que descartar que sea solo una impresión de la interfaz.
- El bucle del Revisor está en `platform/engine/routing.py` (`make_review_router`): puntuación < umbral y vueltas < `max_loops` → vuelve al **Redactor**. Eso coincide con la etapa 6 → 5 del framework.
- **Tras agotar las vueltas (3) el flujo avanza igualmente** hacia Formateador y Publicador (`return siguiente`), aunque el borrador siga rechazado. No existe el estado «requiere revisión humana».

### 0.4 Fuentes que consulta el Investigador

- **Solo RAG local (Qdrant).** `run_investigador` busca en los buckets `["investigador", LIBRARY_AGENT]`, o solo en `rag_doc_ids` si el usuario los eligió. Si hay documentos seleccionados, un guardián descarta lo que no esté seleccionado.
- **No hay búsqueda externa** (Crossref, OpenAlex, EuropePMC): no aparecen en ningún `.py` del backend. La herramienta `search` de `capabilities/tools.py` usa arXiv y Wikipedia, y el Investigador no la invoca.
- Las fuentes que produce llevan **`year`, `journal`, `doi` y `url` siempre vacíos** (`seen_docs[...]` los inicializa a `""` y nada los rellena). Solo se completan `title` y `authors` (extraídos del documento). Esto explica por sí solo referencias sin año ni revista (H-01).
- La «Síntesis» paramétrica del LLM se añade como fuente con `url: synthesis://investigador`; el Formateador la excluye de la bibliografía.
- Sin resultados RAG, el flujo **no se abstiene**: sintetiza desde conocimiento paramétrico y sigue (`research_chunks` de «Contexto base»).

### 0.5 ¿El Publicador invoca un LLM?

**No.** `run_publicador` no llama a `call_llm`. El «parámetro de modelo» que se observó es un artefacto de la traza: `use_cases.py` (≈ línea 308) rellena `model` con `resolve_agent_model(...)` para **todos** los agentes, que siempre devuelve alguno (cae al default del proveedor). El perfil `publicador.agent.md` tiene `model: null`. Por tanto la compuerta **no es un no-op disfrazado: no existe**. 0 tokens y 165 ms son coherentes con escribir en BD y maquetar.

Defectos adicionales del Publicador: publica **siempre**; `published_url` y los metadatos (`indexed: True`, licencia `CC-BY-4.0`) son constantes; si falla la BD solo se registra el error y aun así devuelve `published_url`; si el artículo no existe, lo registra y continúa.

### 0.6 Semántica de la selección RAG

- **Colección:** `collection_for_state` compone `p_<project_id>__<bucket>`. El bucket sale de `rag_collection` del perfil del agente (por defecto `rag_docs`).
- **Sin selección manual:** se buscan los buckets `investigador` **y** la biblioteca compartida `__library__`, de modo que un documento de la biblioteca (p. ej. el de bienvenida, que la siembra de desarrollo crea en `main.py`) puede entrar en el contexto.
- **Con selección manual (`rag_doc_ids`):** manda sobre el bucket y se filtra por esos documentos. Además `routers/agents.py` propaga esa selección a **todos** los agentes del flujo.
- **El Redactor hace su propia consulta RAG** (`limit=10`, mismo criterio de buckets) y la **añade** al `research_data`; esas fuentes no pasan por `sources`, así que pueden usarse en el texto sin figurar en Referencias.
- **No hay umbral de similitud efectivo:** `RAG_SCORE_THRESHOLD` existe en `core/config.py` pero **ningún llamador lo pasa** a `semantic_search_results`, que usa `0.0` por defecto. Además, si la búsqueda semántica falla, `_fetch_agent_results` devuelve fragmentos **sin ranking**.
- `top_k` = `RAG_TOP_K` (6) para el Investigador.

### Hallazgos nuevos relevantes para la Fase 1 y 3

| # | Hallazgo | Dónde |
|---|---|---|
| N1 | **El Revisor falla abierto.** Sin JSON válido, `approval_score` queda en 85 y aprueba; con error del LLM inventa una revisión (75 en la primera vuelta, 90 después, con comentarios fijos). | `revisor.py`, bloques `except` y valor inicial `approval_score = 85` |
| N2 | El prompt del Revisor se presenta como «Senior Software Engineer … LLMOps», no como revisor científico, y no usa `output_language` (H-08). | `revisor.py`, `prompt` |
| N3 | El Revisor usa `llama3.2:1b` por defecto en Ollama (decisión de SPEC-025/T13.4). | `projects/alejandria-magazine/agents/revisor.agent.md` |
| N4 | **El Publicador salta el flujo humano existente.** `/articles/{id}/submit` → `/approve` (revisor asignado o admin) → `PUBLISHED` ya existe, pero el agente marca `PUBLISHED` directamente. La aprobación humana existente registra `reviewer_id` y `published_at`, no la versión aprobada. | `routers/articles.py` (`submit`, `approve`), `publicador.py` |
| N5 | El Formateador acepta la reescritura del LLM si mide ≥ 50 % del original y no contiene frases de rechazo; **no compara contenido** antes/después. | `formateador.py`, `run_formateador` |
| N6 | `format_source_deterministic` omite los campos vacíos en vez de fallar: una fuente sin año/revista se imprime igual. Si no hay título cae a «Documento sin título» o al nombre de archivo. | `formateador.py`, `_clean_source_fields` |
| N7 | `RAG_SCORE_THRESHOLD` es configuración muerta. | `core/config.py` |

---

## 2. Matriz por criterio (0.7)

| Criterio | Estado | Evidencia en código | Fase del plan |
|---|---|---|---|
| **V01** Ficha de estudio (tipo de estudio, clase de I+D, perfil) | **ausente** | Sin rastro de `study_type`, ficha ni perfil de reporte en `app/` ni `projects/`. | F4 (4.2) |
| **V02** definición pendiente | — | El Revisor no emite estado por criterio. | F3 |
| **V03** definición pendiente | — | Sin compuerta determinista. | F1 |
| **V04** definición pendiente | — | Sin compuerta determinista. | F1 |
| **V05** Protocolo sellado (fecha + huella + desviaciones) | **ausente** | `hashlib` solo se usa en `rag.py` para ids de fragmentos, no para sellar protocolos. | F4 (4.3) |
| **V06** definición pendiente | — | — | F1 |
| **V07** Registro de búsqueda (base, cadena, fecha, criterios) | **ausente** | El Investigador solo loguea la *query*; no se persiste un registro de búsqueda ni hay base bibliográfica externa. | F4 (4.1, 4.9) |
| **V08** definición pendiente | — | — | F1 |
| **V09** Referencias válidas (estructura y existencia) | **parcial → casi ausente** | Estructura: `format_source_deterministic` formatea pero **no valida** que haya DOI/autores/año/revista. Existencia: sin Crossref/OpenAlex. Fuentes salen con `doi/year/journal` vacíos (`investigador.py`). | F1 (1.2, 1.3) |
| **V10** Soporte de la cita por el pasaje | **ausente** | El Revisor no comprueba pasajes ni citas; solo puntuación global. | F3 (3.3) |
| **V11** definición pendiente | — | — | F1 |
| **V12** Declaración de uso de IA | **parcial** | La traza `agent_run_steps` registra modelo, parámetros y tokens por paso (SPEC-014/T9.1), pero **no se genera ninguna declaración** para el manuscrito. | F5 (5.1) |
| **V13** Autor humano responsable | **parcial** | `ArticleModel.author_id`/`authors` existen; no hay campo «autor responsable» obligatorio ni comprobación de que ningún agente figure como autor. | F5 (5.2) |
| **V14** CRediT, conflictos de interés, financiamiento | **ausente** | Sin `credit`, `conflict` ni `funding` en el backend. | F5 (5.3) |
| **V15** definición pendiente | — | El Revisor no lo evalúa por separado. | F3 |
| **V16** Datos/código y metadatos FAIR | **parcial** | Publicador fija `license: CC-BY-4.0` y `publisher` como constantes; sin identificador, procedencia ni declaración de datos/código. | F5 (5.4) |

### Barreras transversales del plan

| Elemento | Estado | Evidencia |
|---|---|---|
| Detector de marcadores `(Author, Year)`, `TODO`… (1.1) | **ausente** | Nada lo busca antes de publicar. |
| Compuerta determinista previa a publicar (1.4, 1.5) | **ausente** | `run_publicador` publica sin validar. |
| Estado «requiere revisión humana» tras 3 vueltas (1.6) | **ausente** | `routing.py` avanza igualmente al agotar vueltas. |
| Aprobación humana antes de `PUBLISHED` (1.7) | **parcial** | Existe `/approve` por revisor asignado/admin, pero el agente la salta; no se registra la versión aprobada. |
| Publicador sin LLM (1.8) | **implementado** en comportamiento; el «parámetro de modelo» es traza (`use_cases.py`). | Ver 0.5. |
| Regla de decisión unificada (1.9) | **ausente** | Solo cuenta `approval_score` y `loop_count`. |
| Enrutado de comentarios solo al Redactor (2.2) | **implementado** | `routing.py`. |
| Formateador sin comentarios de contenido (2.3) | **parcial** | No lee `feedback`, pero tampoco hay verificación por diferencia (N5). |
| Esquemas por agente (2.1) | **ausente** | Un solo `AgentState`. |
| Registro por transición de agente/modelo/sección (2.4) | **parcial** | `agent_run_steps` guarda agente, modelo, parámetros, tokens y decisión; no «sección afectada». |
| Redactor limitado a fuentes de las tablas de evidencia (2.5) | **ausente** | El Redactor añade su propio RAG sin pasar por `sources` (0.6). |
| Revisor con JSON por criterio y reintento (3.1) | **ausente** | Esquema de tres campos; falla abierto (N1). |
| Búsqueda externa (4.1) | **ausente** | Ver 0.4. |
| Umbral de similitud (4.5) | **ausente** | `RAG_SCORE_THRESHOLD` sin uso (N7). |
| Separar contexto de fuente citable (4.6) | **parcial** | La síntesis paramétrica se excluye de Referencias, pero la biblioteca compartida sí entra como fuente. |
| Abstención por suficiencia de evidencia (4.7) | **ausente** | Cae a conocimiento paramétrico. |

---

## 3. Qué cambia respecto a lo que suponía el informe

- «No evidenciado» sobre el Publicador queda resuelto: **no hay LLM ni compuerta**; el modelo es un artefacto de traza.
- Un hallazgo que el informe no recoge y es el de mayor riesgo: **el Revisor aprueba por defecto** cuando falla (N1). Con modelos pequeños, un Revisor roto puede producir un 85 que pase.
- La aprobación humana **ya existe** en la plataforma (`/approve`), así que 1.7 es de **reconectar** (que el agente deje el artículo `IN_REVIEW` y registre la versión aprobada), no de construir desde cero.

## 4. Pendiente para cerrar la Fase 0

- [ ] **0.1:** aportar los artefactos completos de PR-FW-001 y archivarlos bajo `docs/reports/PR-FW-001/`.
- [ ] Aportar el texto del Framework v0.1 para completar los criterios marcados «definición pendiente».
- [ ] Confirmar con los artefactos quién recibe los comentarios del Revisor en el Formateador/Publicador (0.3).
- [ ] Decisiones D1–D5 del plan (condicionan las fases 3, 4 y 5).
