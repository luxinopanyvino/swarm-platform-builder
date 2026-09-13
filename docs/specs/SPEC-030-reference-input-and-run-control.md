# SPEC-030: Entrada de referencia y control de la ejecución

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-09-13
- **Épica:** E18 (GitHub Project)
- **ADR relacionado:** se apoya en [SPEC-013](SPEC-013-structural-refactor-project-independence.md) (T8.3/T8.4) · fine-tune en [SPEC-031](SPEC-031-format-learning-finetune.md)
- **Severidad:** 🟠

## 1. Problema

Las dos vistas —subir referencia y seguir la generación— se apoyan en cosas que ya
existen, y **cada una añade una pieza que hoy no está y que no es el detalle de
interfaz que parece**.

**Lo que ya hay.** La subida e indexación de documentos funciona
(`routers/agents.py`: extrae texto, trocea, `ensure_collection`, `upsert_chunks`).
`ExecutionPage.jsx` (508 líneas) ya consume el SSE del pipeline y pinta el log en
vivo: entiende `agent_start`, `token`, `await_decision` y `log`.

**Lo que falta, y por qué importa:**

1. **Un archivo de referencia atado a *este* paper.** Hoy toda subida va al bucket
   compartido `__library__`, que es el que **todos** los agentes del proyecto leen
   además del suyo. Subir ahí la plantilla de estilo de un paper concreto significa
   que todos los papers siguientes recuperarán el estilo de este. Es contaminación
   silenciosa de la biblioteca: nadie la ve hasta que los papers empiezan a
   parecerse entre sí sin que nadie lo haya pedido.

2. **«Agentes participantes» no es una lista de casillas.** La forma del pipeline
   **es un dato** (T8.3): `template.yaml` declara la secuencia y los bucles de
   revisión, y `platform/projects/` los **valida al cargar** —capacidad
   inexistente, nodo no declarado, perfil que falta— precisamente para que el error
   salga al principio y no a mitad de la ejecución. Elegir un subconjunto de
   agentes por ejecución es construir una **variante del `GraphSpec`**, y si no
   pasa por la misma validación, quitar el Revisor deja un bucle
   Revisor→Redactor apuntando a un nodo que no existe — y eso reventaría en el
   minuto ocho, que es justo lo que T8.4 se construyó para evitar.

3. **«Notas adicionales para el enjambre» es texto libre que acaba en un prompt.**
   Es una superficie de inyección y, además, cambia el comportamiento que el gate
   EDD mide. Necesita límite, tratamiento como dato y quedar **registrado en la
   traza**: si una nota cambió el resultado, la explicabilidad tiene que poder
   decirlo.

4. **El progreso porcentual por agente no existe.** El pipeline emite
   `agent_start` y `token`; no emite unidades de trabajo. Un «Redactor 40 %»
   calculado a ojo —por tokens emitidos, por tiempo transcurrido— es **peor que una
   barra indeterminada**: tiene la precisión de un dato y el valor de una
   suposición, y la gente toma decisiones con él («le falta poco, espero»).

## 2. Objetivos / No-objetivos

- **Objetivos:** subir una referencia de formato **acotada a un paper** sin
  contaminar la biblioteca; elegir agentes participantes con la misma validación
  que el grafo del proyecto; notas registradas y acotadas; y un seguimiento de
  ejecución que refleje el pipeline real —bucle de revisión y pausa humana
  incluidos— sin inventar precisión.
- **No-objetivos:** el modo **fine-tune**, que se decide en
  [SPEC-031](SPEC-031-format-learning-finetune.md) y aquí solo aparece como opción
  no disponible; rediseñar el Flow Designer, que ya edita la forma del pipeline;
  edición del `template.yaml` desde la interfaz.

## 3. Criterios de aceptación (Given/When/Then)

- [ ] **AC1** — *Given* un archivo de referencia subido para un paper concreto,
  *When* se indexa, *Then* queda **acotado a ese paper**: los agentes lo recuperan
  al generarlo y **no** aparece en las recuperaciones de otros papers del proyecto;
  verificable con dos papers en el mismo proyecto.
- [ ] **AC2** — *Given* una selección de agentes participantes, *When* se lanza la
  ejecución, *Then* la selección se valida como variante del `GraphSpec` con las
  **mismas** comprobaciones que al cargar el proyecto, y una combinación inválida
  —por ejemplo un bucle de revisión cuyo nodo se ha quitado— se rechaza **antes de
  empezar**, con el motivo; nunca a mitad de la ejecución.
- [ ] **AC3** — *Given* notas adicionales, *Then* tienen longitud máxima declarada,
  se tratan como dato (nunca como instrucción de sistema) y quedan registradas en
  la traza del paso que las usó, de modo que `/explain` pueda atribuirles un cambio
  de resultado.
- [ ] **AC4** — *Given* una ejecución en curso, *When* se mira el seguimiento,
  *Then* el estado de cada agente refleja el pipeline **real**, incluidos el bucle
  Revisor→Redactor —una segunda pasada del Redactor se ve como tal y no como
  retroceso inexplicado— y la pausa por decisión humana (`await_decision`).
- [ ] **AC5** — *Given* un agente en ejecución, *Then* la interfaz muestra progreso
  **fraccional solo si el agente emite unidades de trabajo reales** (por ejemplo
  «sección 2 de 5»); si no las emite, muestra un estado indeterminado. **Queda
  prohibido** derivar un porcentaje de tokens emitidos o de tiempo transcurrido.
- [ ] **AC6** — *Given* el selector de modo de aprendizaje del formato, *Then* la
  opción RAG funciona y la de fine-tune aparece **no disponible con el motivo
  visible** mientras SPEC-031 no esté decidida; el modo elegido queda registrado en
  la ejecución.
- [ ] **AC7** — *Given* una ejecución lanzada desde esta pantalla, *Then* sus
  parámetros —referencia, agentes, notas, modo— quedan en la traza, de forma que
  dos ejecuciones del mismo paper con parámetros distintos sean distinguibles a
  posteriori.

## 4. Diseño propuesto

**El acotamiento de la referencia (AC1)** es la decisión de fondo. El bucket del
agente y `__library__` son los dos espacios que hay hoy; hace falta un tercer
alcance: *documento de esta ejecución*. La opción que menos mecanismo añade es
etiquetar el documento con el artículo al indexarlo —la traza ya guarda
`rag_sources` con `doc_id`— y que la recuperación prefiera y filtre por él cuando
la ejecución declara una referencia. El nombre de la colección **sigue derivándose**
en `project_context.py`: esto es un filtro dentro del espacio del proyecto, no un
espacio nuevo, y no debe abrir una vía para componer nombres de colección a mano.

**La variante del grafo (AC2)** se construye en `platform/engine/` a partir del
`GraphSpec` del proyecto, no en paralelo: quitar un nodo produce un `GraphSpec`
nuevo que pasa por el mismo validador. Así la comprobación no se duplica y no puede
divergir. El motor no menciona agentes concretos, y esto no lo cambia.

**El progreso honesto (AC5).** El camino recto es que el agente que **sabe**
cuántas unidades tiene —el Redactor conoce sus secciones— emita un evento de
progreso por SSE junto a los que ya existen. Los que no lo saben no emiten nada y
la interfaz los muestra indeterminados. Es más trabajo que una barra falsa y es la
diferencia entre informar y decorar.

**Ficheros afectados:** `backend/app/platform/engine/` (variante de `GraphSpec`),
`backend/app/platform/capabilities/rag.py` (alcance por documento),
`backend/app/routers/agents.py` (parámetros de ejecución), el emisor SSE,
`frontend/src/platform/` y `frontend/src/projects/alejandria-magazine/pages/ExecutionPage.jsx`.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| La referencia contamina `__library__` | Todos los papers siguientes heredan el estilo de uno | AC1 con test de dos papers: es el caso que hoy fallaría |
| Un subconjunto de agentes rompe el bucle de revisión en ejecución | Fallo en el minuto ocho, justo lo que T8.4 evitó | AC2: misma validación que al cargar, antes de arrancar |
| Las notas libres se cuelan como instrucción | Inyección en el prompt del agente | AC3: longitud acotada y tratadas como dato; se registran para poder auditarlas |
| Un porcentaje inventado | Decisiones tomadas sobre una cifra sin respaldo | AC5 lo prohíbe explícitamente; indeterminado es una respuesta válida |
| Los parámetros por ejecución cambian el comportamiento que mide el gate EDD | Regresiones atribuidas al modelo cuando eran de configuración | AC7: quedan en la traza, que es de donde lee el harness |

## 6. Plan de pruebas

AC1 con dos papers en un proyecto y una recuperación que debe ver uno y no el otro.
AC2 recorriendo las combinaciones inválidas —bucle sin su nodo, secuencia vacía,
agente no declarado— y exigiendo rechazo **antes** de arrancar. AC5 con un test que
falle si aparece un porcentaje derivado de tokens o de tiempo. AC3, AC4 y AC7 sobre
la traza resultante.

## 7. Impacto operativo / observabilidad

Los eventos SSE ganan un tipo (progreso) que los clientes antiguos deben poder
ignorar. La traza gana los parámetros de ejecución. Sin migraciones si los
parámetros caben en el `params` que ya existe.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E18
  title: "Entrada de referencia y control de la ejecución"
  area: area/ux
tasks:
  - id: T18.1
    title: "Alcance de documento por ejecución: la referencia no contamina la biblioteca"
    sev: high
    depends_on: []
    acceptance: [AC1]
  - id: T18.2
    title: "Agentes participantes como variante validada del GraphSpec"
    sev: high
    depends_on: []
    acceptance: [AC2]
  - id: T18.3
    title: "Notas del enjambre acotadas, tratadas como dato y registradas en la traza"
    sev: medium
    depends_on: []
    acceptance: [AC3, AC7]
  - id: T18.4
    title: "Evento SSE de progreso para los agentes que conocen sus unidades de trabajo"
    sev: medium
    depends_on: []
    acceptance: [AC5]
  - id: T18.5
    title: "Pantalla de subida de referencia y configuración de la ejecución"
    sev: medium
    depends_on: [T18.1, T18.2, T18.3]
    acceptance: [AC6, AC7]
  - id: T18.6
    title: "Seguimiento de ejecución con bucle de revisión, pausa humana y progreso honesto"
    sev: medium
    depends_on: [T18.4]
    acceptance: [AC4, AC5]
```
