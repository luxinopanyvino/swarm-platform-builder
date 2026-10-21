# SPEC-032 — Compuerta de publicación: checklist de calidad de requisitos

- **Propósito:** «tests unitarios» de la redacción de la spec: ¿están los requisitos completos, claros, consistentes y medibles? No comprueba la implementación.
- **Created:** 2026-10-21
- **Source spec:** [`docs/specs/SPEC-032-publication-gate-framework.md`](../SPEC-032-publication-gate-framework.md)
- **Profundidad:** estándar · **Audiencia:** revisión de PR de la spec · **Foco:** compuerta de publicación y calidad de requisitos (valores por defecto de la skill)

## Requirement Completeness

- [x] CHK001 ¿Está definido qué pasa con el artículo cuando la compuerta **sí tiene** bloqueantes (estado final, quién lo ve, a quién vuelve)? AC8 solo cubre el caso «sin bloqueantes»; FW §3 pide devolverlo al agente responsable del criterio que falla. [Gap, Spec §3 AC8; FW §3]
- [x] CHK002 ¿Se especifica cómo se **vuelve a evaluar la compuerta** tras corregir o editar el texto, dado que `approve` devuelve 409 si el texto cambió desde la evaluación? [Gap, Spec §3 AC8]
- [x] CHK003 ¿Hay un requisito para los artículos **ya `PUBLISHED`** o `IN_REVIEW` que no tienen informe de compuerta ni `responsible_author_id` (datos heredados al migrar)? [Gap, Spec §4/§7]
- [ ] CHK004 ¿Se define el comportamiento para fuentes que ni Crossref ni OpenAlex indexan (informes técnicos, tesis, literatura gris, páginas web, libros)? [Gap, Spec §3 AC3]
- [x] CHK005 ¿Se definen el nombre y la carga del evento SSE de «requiere revisión humana»? [Gap, Spec §3 AC7]
- [x] CHK006 ¿Hay un requisito (no solo un riesgo) para el modo de despliegue que registra sin bloquear, con su variable y su valor por defecto? Aparece en §5 y §7 pero no en §3. [Gap, Spec §5/§7]
- [x] CHK007 ¿Está especificado qué se envía a Crossref/OpenAlex (solo metadatos de la referencia, nunca el texto) como requisito verificable y no solo como mitigación de riesgo? [Gap, Spec §5]
- [x] CHK008 ¿Se especifica la política de **retención** de los informes de compuerta (plazo, borrado) y no solo que `data-retention.md` se actualiza? [Completeness, Spec §7]
- [x] CHK009 ¿Se define cómo el autor **aporta un DOI a mano** (dónde, quién, formato, validación) y cómo se registra esa aportación? [Gap, Spec §2/§3 AC3]

## Requirement Clarity

- [x] CHK010 ¿«Bloqueantes de juicio abiertos» está definido para la Fase 1, cuando el Revisor aún no emite estado por criterio (no-objetivo)? AC7 y AC10 dependen de un concepto que esta fase no produce. [Ambiguity, Spec §2/§3 AC7, AC10]
- [x] CHK011 ¿Está enumerada la lista **cerrada** de patrones de marcador de posición (`(Author, Year)`, `[?]`, `TODO`, `XXX`…) y cómo se decide que algo está «fuera de un bloque de código»? El plan dice «y patrones similares». [Ambiguity, Spec §3 AC1]
- [x] CHK012 ¿Se distingue un marcador real de un uso legítimo (un manuscrito que **habla de** citas «(Author, Year)»)? [Ambiguity, Spec §3 AC1]
- [x] CHK013 ¿Están cuantificados el **tiempo máximo por consulta**, los reintentos y el tamaño/TTL de la caché que sustentan la falla cerrada? [Clarity, Spec §3 AC4/§4 — diferido en la clarificación]
- [x] CHK014 ¿Es medible «una sola función decide» (AC10), por ejemplo como un único punto de llamada verificable, o es solo una intención de diseño? [Measurability, Spec §3 AC10]
- [ ] CHK015 ¿Está definido qué es «autor responsable declarado» (campo, obligatoriedad, quién lo rellena y cuándo) y su relación con el usuario que lanzó el pipeline? [Ambiguity, Spec §3 AC8 / Clarifications]
- [ ] CHK016 ¿Se precisa «coincide al menos la mitad de los demás autores» cuando una de las listas es parcial o trae «et al.»? [Clarity, Spec Clarifications 2]
- [ ] CHK017 ¿Se define cómo se normalizan los alias y abreviaturas de revista (fuente del diccionario)? [Gap, Spec Clarifications 2]
- [x] CHK018 ¿Está definido el criterio de elección cuando la búsqueda por título y autores devuelve **varios candidatos** o una coincidencia dudosa? [Ambiguity, Spec §3 AC3]

## Requirement Consistency

- [x] CHK019 **Conflicto:** AC2 hace bloqueante una referencia «sin identificador», pero AC3 permite resolverla por título y autores cuando no lo tiene. ¿Está definido el **orden** (resolver y enriquecer antes de validar la estructura)? [Conflict, Spec §3 AC2 vs AC3]
- [x] CHK020 ¿Es coherente AC10 («cero bloqueantes de juicio») con el no-objetivo «salida del Revisor por criterio» y con AC7 (3 vueltas con bloqueantes de juicio)? [Conflict, Spec §2 vs §3]
- [x] CHK021 ¿Es coherente AC8 («nunca `PUBLISHED` desde el Publicador») con el endpoint `publish` que ya existe en `routers/articles.py`? [Consistency, Spec §3 AC8 / §4]
- [x] CHK022 ¿Es coherente que AC8 exija que quien aprueba sea «distinto de quien lanzó el pipeline» con despliegues de **un solo usuario** (desarrollo, equipos pequeños) donde esa persona es también el único administrador? [Consistency, Spec Clarifications 3]
- [x] CHK023 ¿Se usa una terminología única para los estados y resultados: `in_review`/`IN_REVIEW`, «no verificado»/`not_verified`, «bloqueante de juicio»/«bloqueante determinista»? [Consistency, Spec §3]
- [x] CHK024 ¿Es coherente la dependencia declarada de **T20.6** (sin dependencias) con que su disparador (bloqueantes de juicio abiertos) solo existe tras **T20.9** (Revisor que no aprueba por defecto)? [Consistency, Spec §8]

## Acceptance Criteria Quality

- [x] CHK025 ¿Tiene cada AC un identificador estable y cada tarea referencia los AC que cubre? [Traceability, Spec §3/§8]
- [x] CHK026 ¿Están los AC redactados en Given/When/Then? [Acceptance Criteria, Spec §3]
- [x] CHK027 ¿Tiene AC3 un **objetivo medible** de resolución (porcentaje mínimo de referencias válidas que deben resolverse) para saber si la opción (a) funciona en la práctica? [Measurability, Spec §3 AC3]
- [x] CHK028 ¿Es verificable AC9 por **un único** mecanismo (test de traza) y se define cómo un agente declara que no usa LLM? [Measurability, Spec §3 AC9 / §4]
- [x] CHK029 ¿Es AC12 («los tests existentes siguen en verde») objetivo, dado que hay 4 fallos preexistentes en `develop`? [Measurability, Spec §3 AC12]

## Scenario Coverage

- [ ] CHK030 ¿Están cubiertos los escenarios alternativos de la aprobación (rechazo con comentario, aprobación por dos personas a la vez, aprobación con la compuerta caducada)? [Coverage, Alternate/Concurrency, Spec §3 AC8]
- [ ] CHK031 ¿Hay requisitos de **recuperación**: qué ocurre si falla la escritura del informe o la migración a mitad de una publicación? [Gap, Recovery, Spec §7]
- [x] CHK032 ¿Se cubre la **reanudación** de una ejecución (`resume`) respecto a la compuerta y al contador de vueltas? [Gap, Spec §3 AC7]
- [ ] CHK033 ¿Se define qué ocurre con una referencia **duplicada** o dos documentos que resuelven al mismo DOI? [Gap, Edge, Spec §3 AC3]
- [ ] CHK034 ¿Se define el caso de un manuscrito **sin ninguna referencia**? [Edge, Spec §3 AC2/AC11]

## Non-Functional Requirements

- [x] CHK035 ¿Hay un requisito de latencia/duración máxima de la compuerta (con N referencias) para no bloquear la ejecución? [Gap, Performance, Spec §7]
- [x] CHK036 ¿Se especifican los límites de uso de las APIs externas (cortesía/ratelimit de Crossref y OpenAlex, identificación del cliente) y el comportamiento ante 429? [Gap, Spec §4]
- [ ] CHK037 ¿Se define qué se registra en logs y métricas y con qué nombres (resultado por criterio, tasa de no verificado por motivo)? [Clarity, Spec §7]
- [x] CHK038 ¿Cubren los requisitos de seguridad la comprobación de que el informe y la aprobación no se pueden falsificar (quién puede escribir/leer `gate-report`)? [Gap, Security, Spec §3 AC6/AC8]

## Dependencies & Assumptions

- [ ] CHK039 ¿Está validada la suposición de que Crossref/OpenAlex cubren el corpus real del proyecto (preprints, español, informes)? [Assumption, Spec §2]
- [x] CHK040 ¿Está documentada la dependencia de SPEC-024 (egress) y su implicación: dos hosts nuevos permitidos y su revalidación en redirecciones? [Dependency, Spec §4]
- [x] CHK041 ¿Se declara la dependencia con la Fase 3 (Revisor por criterio) y con la Fase 4 (metadatos del Investigador), y qué se rehace al llegar? [Dependency, Spec §2]

## Ambiguities & Conflicts

- [x] CHK042 ¿Se resolvió dónde viven las reglas de la compuerta frente a las de flujo (`gate:` vs `flow_rules`), y se corrigió la referencia incompleta «SPEC-… de flujo» en §4? [Ambiguity, Spec §4]
- [x] CHK043 ¿Está acotado V03 a un diccionario de títulos de sección por idioma (Introducción/Introduction, Métodos/Metodología/Methods), ya que el Redactor genera «Metodología»? [Ambiguity, Spec §3 AC11]
