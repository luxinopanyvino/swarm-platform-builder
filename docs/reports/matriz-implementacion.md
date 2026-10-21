# Matriz de implementación — Fase 0 del plan de mejoras del pipeline

- **Fecha:** 2026-10-21
- **Base:** `develop` en `1fb850e` (más #426 aún sin mergear, no relevante aquí)
- **Alcance:** diagnóstico **solo de lectura** del backend (tareas 0.2 a 0.7 del plan). No se ha cambiado código.
- **Origen:** informe «Framework vs. plataforma actual» (PR-FW-001, 20/10/2026) y plan de implementación de mejoras.

## Limitaciones de este documento (leer antes de las tablas)

1. **Falta la tarea 0.1.** Los artefactos de PR-FW-001 (salidas intermedias, texto antes/después del Formateador, logs) no están en el repositorio. Sin ellos, aquí se afirma lo que **dice el código**, no lo que ocurrió en esa ejecución. Hay que aportarlos.
2. **Criterios V01–V16:** definidos en el *Framework de redacción y validación de papers* v0.1 (29/09/2026), §9, que no está en el repo (se recibió como PDF). La matriz usa esas definiciones, con su tipo (bloqueante/advertencia) y su verificación (automática/juicio).
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

Definiciones del Framework v0.1 §9. «Quién lo comprueba» es lo que fija el framework (§10): la compuerta determinista del Publicador (etapa 8) o el Revisor (etapa 6).

| Criterio (Framework §9) | Tipo · verificación | Quién | Estado | Evidencia en código | Fase |
|---|---|---|---|---|---|
| **V01** Tipo de estudio, clase de I+D y guía/perfil de reporte registrados en la ficha | Bloqueante · automática | Compuerta | **ausente** | Sin `study_type`, ficha ni perfil en `app/` ni `projects/`. Los perfiles del framework (PRISMA, TRIPOD-LLM, DSRM, Frascati, Oslo/TRL…) no existen en el sistema. | F4 (4.2) |
| **V02** Cada ítem aplicable de la guía/perfil apunta a su ubicación en el texto | Bloqueante · automática + muestreo | Revisor | **ausente** | El Revisor no carga ninguna guía ni emite estado por criterio (`revisor.py`). | F3 |
| **V03** Estructura del perfil completa y en orden (IMRaD por defecto) | Bloqueante · automática | Compuerta | **parcial** | El prompt del Redactor pide «Resumen, Introducción, Metodología, Resultados y Discusión Preliminares» (`redactor.py`, plantillas ~l. 26/41): Resultados y Discusión van **fundidos** y no hay Referencias ni Declaraciones finales en el mandato. Nadie valida estructura ni orden. | F1 |
| **V04** El título identifica el diseño cuando la guía lo pide | Bloqueante · automática | Compuerta | **ausente** | Sin comprobación del título. | F1 |
| **V05** Objetivos/resultados primarios coinciden con el protocolo sellado; desviaciones registradas | Bloqueante · automática | Compuerta | **ausente** | No hay protocolo sellado: `hashlib` solo se usa en `rag.py` para ids de fragmentos. | F4 (4.3) |
| **V06** Todos los resultados primarios declarados aparecen en Resultados | Bloqueante · automática | Compuerta | **ausente** | Depende de V05; sin protocolo no hay qué comparar. | F1 / F4 |
| **V07** Búsqueda reproducible: bases, fechas, cadenas, criterios | Bloqueante **solo en revisiones** · automática | Compuerta | **ausente** | El Investigador solo loguea la *query*; no se persiste registro de búsqueda ni hay base externa. | F4 (4.1, 4.9) |
| **V08** Diagrama de flujo de selección de estudios | Bloqueante **solo en revisiones** · automática | Compuerta | **ausente** | Sin cribado ni diagrama. | F4 |
| **V09** Toda referencia tiene origen recuperado y existe con metadatos coincidentes | Bloqueante · automática | Compuerta | **parcial → casi ausente** | Origen: las fuentes vienen de RAG local, no de una base bibliográfica. Existencia: sin Crossref/OpenAlex. `investigador.py` deja `doi/year/journal/url` vacíos y `format_source_deterministic` formatea sin validar. | F1 (1.2, 1.3) |
| **V10** Cada afirmación citada está respaldada por el pasaje de la fuente | Bloqueante · agente independiente + muestra humana | Revisor | **ausente** | El Revisor da una puntuación global; no ve pasajes ni citas. | F3 (3.3) |
| **V11** Ninguna fuente citada está retractada | Bloqueante · automática | Compuerta | **ausente** | Sin fuente de retractaciones. | F1 |
| **V12** Declaración de uso de IA completa (herramienta, versión, tarea, ubicación) contra el registro de agentes | Bloqueante · automática | Compuerta | **parcial** | `agent_run_steps` registra agente, modelo, parámetros y tokens por paso (SPEC-014/T9.1): hay **registro**, pero no versión del modelo, sección afectada ni declaración generada en el manuscrito. | F5 (5.1) |
| **V13** Ningún agente figura como autor; hay autor humano responsable | Bloqueante · automática | Compuerta | **parcial** | `ArticleModel.author_id`/`authors` existen; no hay «autor responsable» obligatorio ni comprobación de que ningún agente aparezca como autor. | F5 (5.2) |
| **V14** Contribuciones en CRediT; conflictos de interés y financiamiento declarados | Bloqueante · automática | Compuerta | **ausente** | Sin `credit`, `conflict` ni `funding` en el backend. | F5 (5.3) |
| **V15** Las conclusiones no afirman más que los resultados; la Discusión incluye limitaciones | **Advertencia** · agente independiente + revisión humana | Revisor | **ausente** | El Revisor puntúa «rigor, claridad, coherencia» en bloque; no evalúa V15 por separado, y el prompt del Redactor ni siquiera pide una sección de limitaciones. | F3 |
| **V16** Declaración de datos y código, y metadatos FAIR completos | **Advertencia** · automática | Compuerta | **parcial** | El Publicador fija `license: CC-BY-4.0` y `publisher` como **constantes**; sin identificador persistente, procedencia ni declaración de datos/código. | F5 (5.4) |

Resumen: **ausente** 11 (V01, V02, V04–V08, V10, V11, V14, V15), **parcial** 5 (V03, V09, V12, V13, V16), **implementado** 0.

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

## 2 bis. Contraste con el Framework v0.1 (§3, §10)

Reglas del framework que el código incumple hoy, además de los criterios:

| Regla del framework | Cita | Código actual |
|---|---|---|
| El Formateador **no modifica el contenido científico** y «el cuerpo no cambia» | §3 etapa 7, §10 | Un LLM **reescribe el manuscrito entero** y se acepta si mide ≥ 50 % (`formateador.py`, N5). |
| El Formateador **compone** declaraciones de IA, CRediT, conflictos, financiamiento y datos desde registros | §10 | No compone ninguna. |
| El Redactor **no puede añadir fuentes** fuera de las tablas de evidencia | §10 | Hace su propia consulta RAG y la añade al contexto (`redactor.py`). |
| El Investigador **no escribe texto del manuscrito** | §10 | Genera una «síntesis» con LLM, incluso desde conocimiento paramétrico si no hay fuentes. |
| El Investigador busca en EuropePMC y OpenAlex y registra la búsqueda | §10 | Solo RAG local. |
| El Revisor emite **JSON por criterio** y **no aprueba sin evidencia por criterio** | §3 etapa 6, §10 | Falla abierto: aprueba con 85 sin JSON válido (N1). |
| Tras 3 vueltas con bloqueantes → «requiere revisión humana», **no se publica** | §3, §10 cambio 4 | Avanza a publicar (`routing.py`). |
| El Publicador **no publica sin la firma del autor responsable** y no usa LLM | §10 | Publica siempre; no usa LLM (cumple lo segundo). |
| **Falla cerrada** si una herramienta de la línea base no responde | §20, regla 4 | Sin herramientas. |

### Implicación de diseño que el plan no recoge (para decidir)

El nivel 1 de V09 exige que **toda referencia entre por recuperación desde una base bibliográfica y traiga identificador (DOI/PMID)**. Hoy las fuentes son documentos que alguien sube al RAG (PDF/MD/TXT), y sus metadatos se extraen del propio texto, sin identificador. Con una aplicación estricta, **casi ninguna fuente subida a mano pasaría V09**. Hace falta decidir entre: (a) resolver cada documento subido contra Crossref/OpenAlex por título/autores para obtener su DOI; (b) permitir una excepción documentada para «documento interno aportado por el autor»; (c) exigir que el corpus entre solo desde la búsqueda externa. Esto condiciona 1.2, 1.3 y 4.1, y es previo a D2.

### Diferencias entre el plan y el framework a revisar

- El plan trata V07 como bloqueante siempre; el framework lo hace bloqueante **solo en revisiones** (V08 igual).
- El plan pide «otra familia» de modelo para el Revisor; el framework solo exige «modelo distinto del Redactor» y deja la familia como propuesta (FW-4).
- La regla del framework para 3.5 (cero omisiones en ≥ 60 defectos por criterio, kappa ≥ 0,80) es de la Capa B y la decide el panel; el mini conjunto del plan sirve solo para elegir modelo, no para certificar.

---

## 3. Qué cambia respecto a lo que suponía el informe

- «No evidenciado» sobre el Publicador queda resuelto: **no hay LLM ni compuerta**; el modelo es un artefacto de traza.
- Un hallazgo que el informe no recoge y es el de mayor riesgo: **el Revisor aprueba por defecto** cuando falla (N1). Con modelos pequeños, un Revisor roto puede producir un 85 que pase.
- La aprobación humana **ya existe** en la plataforma (`/approve`), así que 1.7 es de **reconectar** (que el agente deje el artículo `IN_REVIEW` y registre la versión aprobada), no de construir desde cero.

## 4. Pendiente para cerrar la Fase 0

- [ ] **0.1:** aportar los artefactos completos de PR-FW-001 y archivarlos bajo `docs/reports/PR-FW-001/`.
- [x] Criterios V01–V16 completados con el Framework v0.1 (recibido como PDF).
- [ ] Versionar el framework en el repo (p. ej. `docs/framework/`) para que sea la fuente de la verdad citable; hoy solo existe como PDF fuera del repo.
- [ ] Confirmar con los artefactos quién recibe los comentarios del Revisor en el Formateador/Publicador (0.3).
- [ ] Decisiones D1–D5 del plan (condicionan las fases 3, 4 y 5).
