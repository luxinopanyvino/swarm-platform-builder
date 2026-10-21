# SPEC-032: Compuerta de publicación según el Framework de validación (Fase 1)

- **Estado:** Draft
- **Autor:** Equipo de plataforma (borrador asistido)
- **Fecha:** 2026-10-21
- **Épica:** E20 (GitHub Project)
- **ADR relacionado:** — (la decisión sobre V09 se registra aquí; si el panel la cambia, pasa a ADR)
- **Severidad:** 🔴

> **Origen.** Plan de implementación de mejoras del pipeline, Fase 1 (tareas 1.1–1.9), a
> partir del *Framework de redacción y validación de papers* v0.1 (29/09/2026) y del
> diagnóstico de código de [`docs/reports/matriz-implementacion.md`](../reports/matriz-implementacion.md).
> Cierra los hallazgos H-01 (referencias incompletas / `(Author, Year)`) y H-03 (sin
> compuerta ni aprobación humana). El framework es la fuente de la verdad de las reglas;
> esta spec solo decide cómo se implementan aquí. Cita sus secciones como «FW §n».

## 1. Problema

Hoy ningún manuscrito con defectos verificables está impedido de llegar a «Publicado»:

- `backend/app/modules/agents/adapters/publicador.py` (`run_publicador`) escribe el texto en
  la BD y marca `PUBLISHED` **sin validar nada**. No existe compuerta (FW §3 etapa 8).
- **Falla abierto el Revisor** (`revisor.py`): sin JSON válido deja `approval_score = 85` y
  aprueba; si el LLM falla, inventa una revisión (75 y 90 con comentarios fijos).
- Tras agotar las 3 vueltas, `platform/engine/routing.py` (`make_review_router`) **avanza
  igualmente** a Formateador y Publicador. FW §3 exige el estado «requiere revisión humana»
  y no publicar.
- La aprobación humana ya existe (`routers/articles.py`: `submit`, `approve`) pero el agente
  **la salta** al marcar `PUBLISHED` directamente; además `approve` solo guarda
  `reviewer_id` y `published_at`, no la versión aprobada.
- Las referencias salen de RAG local con `doi`, `year`, `journal` y `url` siempre vacíos
  (`investigador.py`), y `format_source_deterministic` (`formateador.py`) **omite** los campos
  que faltan en lugar de fallar, de modo que un nombre de archivo acaba como «referencia»
  (H-01). Nada comprueba que exista (FW §7, niveles 1 y 2).
- El «modelo» que aparece en la traza del Publicador es un artefacto: `use_cases.py`
  rellena `model` para **todos** los agentes aunque no llamen al LLM.

El framework fija que se publica solo si se cumplen **tres** condiciones: (1) Revisor ≥ 80 sin
bloqueantes de juicio abiertos, (2) compuerta determinista sin bloqueantes sobre el **texto
final tras el Formateador**, (3) aprobación humana explícita (FW §3, regla de decisión).

## 2. Objetivos / No-objetivos

- **Objetivos**
  - Compuerta determinista, sin LLM, en el Publicador, sobre el texto final.
  - Detector de marcadores de posición y validación de estructura y existencia de
    referencias (V09) contra Crossref/OpenAlex, **con falla cerrada**.
  - Informe de compuerta persistido y versionado por texto evaluado.
  - Estado «requiere revisión humana» tras 3 vueltas con bloqueantes.
  - Aprobación humana explícita, registrada, que vincula usuario, decisión, fecha y versión.
  - Publicador sin LLM, también en la traza.
  - Regla de decisión unificada, implementada una sola vez.
- **Decisión de V09 (opción «a», sin excepciones).** Cada documento que alimenta Referencias
  se **resuelve contra Crossref/OpenAlex por DOI o, si no lo tiene, por título y autores**,
  y se verifica la coincidencia de título, autores, año y revista. Lo que no se resuelve
  queda **«no verificado»** y bloquea. El autor puede **aportar el DOI a mano**, que entra
  por el mismo camino de verificación. *Se descartan* la excepción para «documento
  interno» (el framework no la prevé: FW §2.4, §7 nivel 1) y la entrada solo por búsqueda
  externa (es la Fase 4, no esta).
- **No-objetivos**
  - Salida del Revisor **por criterio** y cambio de modelo (Fase 3). Aquí solo se corrige que
    falle abierto y se define cómo cuenta su resultado en la decisión.
  - Búsqueda bibliográfica externa, ficha de estudio, protocolo sellado y registro de
    búsqueda (Fase 4); declaraciones de IA, CRediT, conflictos y FAIR (Fase 5).
  - V10 (soporte de la cita), V11 (retractaciones: exige una fuente abierta que no hay aún),
    V15 y V02: son de juicio o necesitan herramientas de fases posteriores.
  - Contratos/esquemas por agente y enrutado de comentarios (Fase 2).
  - Control de similitud textual/plagio (decisión abierta del panel, FW §19).

## 3. Criterios de aceptación (Given/When/Then)

- [ ] **AC1** — *Marcadores de posición* *Given* un texto final con `(Author, Year)`, `[?]`,
  `TODO` o `XXX` fuera de un bloque de código · *When* corre la compuerta · *Then* hay un
  resultado **bloqueante** que nombra el patrón y su posición, y el artículo no pasa a
  `PUBLISHED`.
- [ ] **AC2** — *Estructura de referencias* *Given* una referencia sin identificador, sin
  autores, sin año o sin publicación (p. ej. solo un nombre de archivo) · *When* corre la
  compuerta · *Then* esa referencia es **bloqueante** y se indica qué campo falta. Un
  campo vacío ya no se omite en silencio al formatear.
- [ ] **AC3** — *Existencia y coincidencia (V09)* *Given* una referencia con DOI, o sin él pero
  con título y autores · *When* se resuelve contra Crossref y, si no aparece, OpenAlex ·
  *Then* pasa solo si existe y coinciden título, autores, año y revista (umbral de
  coincidencia declarado en la configuración); una discrepancia es bloqueante y una
  referencia sin resolver es «no verificado» y también bloquea. Si el autor aporta un DOI
  a mano, se verifica por este mismo camino.
- [ ] **AC4** — *Falla cerrada* *Given* que Crossref y OpenAlex no responden (error, tiempo
  agotado o respuesta inválida) · *When* corre la compuerta · *Then* las referencias quedan
  «no verificado», el criterio **no se aprueba** y el motivo consta en el informe. Nunca
  se aprueba por ausencia de respuesta.
- [ ] **AC5** — *Posición y alcance de la compuerta* *Given* un flujo completo · *When*
  termina el Formateador · *Then* la compuerta se evalúa sobre `formatted_text` (el texto
  que se publicaría), no sobre el borrador, y cada criterio del conjunto en vigor obtiene
  exactamente uno de: `passed`, `failed`, `not_verified`, `not_implemented`.
- [ ] **AC6** — *Informe persistido* *Given* una evaluación de la compuerta · *When* termina ·
  *Then* se guarda un informe con estado y evidencia por criterio, la huella (SHA-256) del
  texto evaluado, la fecha y la ejecución, y se puede leer por API y verlo desde el artículo.
  Una nueva evaluación crea otro informe: no sobrescribe el anterior.
- [ ] **AC7** — *Revisión humana tras 3 vueltas* *Given* que se agotan las 3 vueltas y siguen
  abiertos bloqueantes de juicio · *When* el enrutador decide el siguiente paso · *Then* el
  artículo pasa a «requiere revisión humana», **no** se ejecutan Formateador ni
  Publicador y se emite el evento SSE correspondiente.
- [ ] **AC8** — *Aprobación humana explícita* *Given* una compuerta sin bloqueantes · *When* el
  Publicador termina · *Then* el artículo queda en `IN_REVIEW` y **nunca** en `PUBLISHED`.
  `approve` registra usuario, decisión, fecha y huella del texto aprobado; se rechaza (409)
  si el texto cambió desde la compuerta o si el último informe tiene bloqueantes.
- [ ] **AC9** — *Publicador sin LLM* *Given* una ejecución completa · *When* corre el Publicador ·
  *Then* no llama al LLM (0 tokens) y su traza no registra modelo (`model` nulo), a diferencia
  de hoy. Un test falla si el módulo importa o invoca `call_llm`.
- [ ] **AC10** — *Regla de decisión unificada* *Given* los tres insumos (revisión, compuerta,
  aprobación) · *When* se evalúa si publicar · *Then* una sola función decide, y solo
  devuelve «publicar» con Revisor ≥ 80, **cero** bloqueantes de juicio, compuerta sin
  bloqueantes y aprobación humana. Un 80 con un bloqueante abierto no publica. Si la revisión
  no se puede interpretar o el LLM falla, el Revisor **no aprueba**: queda «no verificado» y
  cuenta como bloqueante (se elimina el 85 por defecto y la revisión inventada).
- [ ] **AC11** — *Regresión* *Given* un manuscrito válido con referencias resueltas · *When*
  recorre el pipeline y recibe aprobación · *Then* llega a `PUBLISHED` y los tests
  existentes siguen en verde.

## 4. Diseño propuesto

**Módulo de compuerta** `backend/app/platform/publication_gate/` (genérico, no nombra agentes):
un registro de criterios, cada uno una función pura `(contexto) -> CriterionResult`. El
Publicador la invoca; el proyecto declara en `template.yaml` (`gate:`) qué criterios se
aplican y con qué parámetros, igual que `flow_rules` en SPEC-… de flujo. Así la compuerta no
vive en código disperso y otro proyecto puede traer la suya.

- **Criterios de esta fase:** marcadores de posición (1.1), estructura de referencias (V09
  nivel 1, 1.2), existencia (V09 nivel 2, 1.3), estructura (V03), y los criterios cuyos datos
  aún no existen (V01, V05–V08, V12–V14, V16) se **declaran** y resultan `not_implemented`
  hasta que su fase los construya.
- **Resolución de referencias** (`reference_resolver.py`): cliente a Crossref y OpenAlex por
  la puerta de salida única `platform/egress.py` (`safe_get`), como exige SPEC-024. Caché de
  resultados positivos con TTL; **nunca** se aprueba desde una respuesta ausente (AC4).
  Coincidencia por similitud normalizada de título/autores, año exacto y revista; el umbral
  se configura.
- **Fuentes con identificador.** El Investigador deja de dejar `doi/year/journal` vacíos:
  conserva lo que el documento traiga y, al resolver, **enriquece** la fuente con los
  metadatos canónicos; el Formateador solo imprime fuentes con campos completos.
- **Informe:** tabla `publication_gate_reports` (migración Alembic, con test de paridad
  `create_all`/migraciones) con `article_id`, `run_id`, `text_sha256`, `criteria` (JSON),
  `created_at`; `GET /api/v1/articles/{id}/gate-report`.
- **Estado «requiere revisión humana»:** nuevo valor de `ArticleStatus`; en `routing.py`, al
  agotar vueltas con revisión rechazada, el router devuelve el fin en lugar de
  `next_after(...)`, y la ejecución lo marca con el nuevo estado.
- **Aprobación:** `run_publicador` deja de escribir `PUBLISHED`; deja el artículo en
  `IN_REVIEW` con el informe. `approve` exige un informe vigente sin bloqueantes cuya huella
  coincida con el cuerpo y guarda `approved_by`, `approved_at`, `approved_text_sha256`.
- **Traza:** `use_cases.py` registra `model = null` para agentes que declaran que no usan LLM.
- **Decisión unificada:** `can_publish(review, gate, approval)` en un único módulo, usado por
  el Publicador y por `approve`; sin copias.
- **Ficheros afectados:** `adapters/publicador.py`, `adapters/revisor.py`,
  `adapters/investigador.py`, `adapters/formateador.py`, `platform/engine/routing.py`,
  `application/use_cases.py`, `routers/articles.py`, `models/`, `alembic/versions/`,
  `projects/alejandria-magazine/template.yaml`, `platform/projects/loader.py`, frontend (estado
  del artículo e informe) y `docs/governance/data-retention.md` (la tabla nueva acumula rastro).

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Con falla cerrada y criterios aún no construidos, **nada podría publicarse** | Bloqueo total del flujo | `not_implemented` es un estado propio y se declara qué criterios **bloquean ya** (ver Clarifications); se retira conforme cada fase los implementa |
| Documentos subidos a mano sin DOI no se resuelven por título | Falsos «no verificado» | El autor aporta el DOI; informe indica el motivo; se mide la tasa de resolución |
| Falsos positivos de coincidencia (títulos parecidos) | Referencia correcta bloqueada | Umbral configurable y evidencia en el informe; revisión humana final |
| Crossref/OpenAlex lentos o caídos | Publicación detenida | Caché de positivos, tiempo máximo por consulta y falla cerrada explícita |
| Enviar títulos de manuscritos no publicados a un servicio externo | Privacidad | Solo se envían metadatos de **referencias** ya citadas, no el texto; se revisan las condiciones de uso (FW §20.7) |
| Flujos y artículos existentes que quedarían bloqueados | Regresión | Modo de despliegue que registra sin bloquear antes de activar (como `FLOW_RULES_ENFORCE`) |
| Cambiar `ArticleStatus` rompe el frontend o filtros | Errores en listados | Migración, test de paridad y revisión de todos los usos del enum |

## 6. Plan de pruebas

- **Unitarias (código determinista, sin muestreo, FW §14):** un caso válido y uno inválido por
  criterio — AC1 (PR-REG-01), AC2 (PR-REG-02), AC3, AC10 (regla de decisión, tabla de
  verdad completa).
- **Falla cerrada:** resolutor simulado que lanza error/tiempo agotado → `not_verified` y
  no aprueba (AC4, PR-REG-12).
- **Integración:** flujo completo con resolutor simulado: referencia válida pasa, inventada
  falla, sin DOI y sin título resoluble queda no verificada; el artículo no llega a `PUBLISHED`
  sin `approve` (AC5, AC6, AC8, PR-REG-05/06); 3 vueltas con bloqueantes no ejecuta el
  Formateador (AC7); `approve` con texto cambiado → 409.
- **Publicador sin LLM:** test estructural y de traza (AC9, PR-REG-11).
- **Migración:** `tests/test_migrations.py` verifica que el esquema migrado coincide con
  `create_all`.
- **Regresión:** suite completa; los 4 fallos preexistentes no empeoran.
- Las definiciones de PR-REG-xx viven en el informe de pruebas, que no está en el repositorio:
  se enlazan aquí por ID.

## 7. Impacto operativo / observabilidad

- Logs y métricas: resultado por criterio, aciertos de caché y tasa de «no verificado» por
  motivo; latencia de Crossref/OpenAlex.
- Nueva tabla y columnas de aprobación: migración Alembic; **retención** de informes
  documentada en `data-retention.md` (hay un test que lo exige).
- Despliegue: modo que registra sin bloquear primero; luego activación. Rollback: desactivar
  el bloqueo por configuración y volver a la migración previa.
- Cambio de comportamiento visible: los artículos ya no quedan `PUBLISHED` al terminar el
  pipeline; pasan a `IN_REVIEW`.

## Clarifications

- **[NEEDS CLARIFICATION] Criterios que bloquean ya.** FW §3 dice que un criterio bloqueante
  no comprobable no se aprueba, pero V01, V05–V08, V12–V14 y V16 no tienen datos hasta las
  Fases 4 y 5: aplicado al pie de la letra, **nada se publicaría** hasta entonces. Propuesta:
  `not_implemented` no bloquea y se lista como pendiente; bloquean desde ya marcadores,
  estructura (V03), referencias (V09) y la decisión unificada. Falta confirmarlo con producto
  y el panel.
- **[NEEDS CLARIFICATION] Umbral de coincidencia** de título/autores/año/revista para V09 y
  si el año admite ±1 (preprint frente a versión publicada).
- **[NEEDS CLARIFICATION] Autor humano aprobador** (D4 del plan): quién puede ejecutar
  `approve` en las pruebas y en producción; hoy lo permite el revisor asignado o un admin.
- **[NEEDS CLARIFICATION] V03 por perfil.** Sin ficha de estudio (Fase 4) solo se puede
  comprobar IMRaD por defecto; el prompt del Redactor funde Resultados y Discusión.
- **[NEEDS CLARIFICATION] Nombre y semántica del nuevo estado** (`requires_human_review`) y su
  transición de vuelta tras la corrección.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E20
  title: "Compuerta de publicación según el Framework de validación (Fase 1)"
  area: area/backend
tasks:
  - id: T20.1
    title: "Detector de marcadores de posición en el texto final"
    sev: high
    depends_on: []
    acceptance: [AC1]
  - id: T20.2
    title: "Validador de estructura de referencias (V09 nivel 1)"
    sev: high
    depends_on: []
    acceptance: [AC2]
  - id: T20.3
    title: "Resolución de existencia contra Crossref/OpenAlex con falla cerrada (V09 nivel 2)"
    sev: high
    depends_on: [T20.2]
    acceptance: [AC3, AC4]
  - id: T20.4
    title: "Compuerta determinista en el Publicador sobre el texto final"
    sev: high
    depends_on: [T20.1, T20.2, T20.3]
    acceptance: [AC5]
  - id: T20.5
    title: "Informe de compuerta persistido y consultable"
    sev: medium
    depends_on: [T20.4]
    acceptance: [AC6]
  - id: T20.6
    title: "Estado «requiere revisión humana» tras 3 vueltas con bloqueantes"
    sev: high
    depends_on: []
    acceptance: [AC7]
  - id: T20.7
    title: "Aprobación humana explícita con registro de usuario, decisión, fecha y versión"
    sev: high
    depends_on: [T20.5]
    acceptance: [AC8]
  - id: T20.8
    title: "Publicador sin LLM, también en la traza"
    sev: low
    depends_on: []
    acceptance: [AC9]
  - id: T20.9
    title: "Regla de decisión unificada y Revisor que no aprueba por defecto"
    sev: high
    depends_on: [T20.4, T20.6, T20.7]
    acceptance: [AC10, AC11]
```
