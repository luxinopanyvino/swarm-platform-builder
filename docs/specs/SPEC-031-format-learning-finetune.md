# SPEC-031: Aprendizaje de formato por fine-tune local

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-09-13 · decisiones de política y paso a `Ready` el 2026-09-15
- **Épica:** E19 (GitHub Project)
- **ADR relacionado:** ADR pendiente — lo produce T19.2 y es **prerrequisito** de cualquier implementación
- **Severidad:** 🟠

> **`Ready` solo para la fase de decisión.** Esta spec nació en `Draft` a propósito:
> sembrar tareas de implementación sobre una decisión no tomada es cómo se construyen
> features a medias. Las cuatro preguntas de política ya tienen respuesta (ver
> [Clarifications](#clarifications)), así que se abren **dos** tareas: el spike que
> mide la viabilidad en el hardware real (T19.1) y el ADR que fija el diseño (T19.2).
> Los criterios y tareas de **implementación** se añaden a esta spec cuando el ADR
> se acepte (AC4); hasta entonces no se escribe código de entrenamiento en
> `backend/app`.

## 1. Problema

La maqueta de subida de referencia ofrece dos modos de aprendizaje del formato como
si fueran equivalentes:

- **RAG — extraer del archivo.** Existe hoy: se indexa y el agente recupera.
- **Fine-tune — entrenamiento local.** No existe nada. `grep -ri "fine.tune\|LoRA"`
  sobre `backend/app` y `frontend/src` no devuelve una sola línea.

Presentados como dos radios uno encima del otro, parecen la misma decisión con
distinto botón. **No lo son, y la diferencia no es de esfuerzo sino de naturaleza.**

**La asimetría que lo decide todo: RAG se puede deshacer; un fine-tune no.** Si un
documento se borra de la biblioteca, su influencia desaparece en la siguiente
recuperación. Si ese documento entró en un entrenamiento, su contenido queda
**dentro de los pesos**, y borrarlo exige reentrenar desde cero — suponiendo que se
sepa qué documentos entraron. Eso choca de frente con
[data-retention.md](../governance/data-retention.md), que fija qué se guarda y
cuánto, y con cualquier petición de supresión.

A eso se suman cuatro cosas que no son detalles de implementación:

- **Aislamiento por proyecto.** T8.5 costó construirlo: la colección se deriva y un
  perfil no puede apuntar al espacio de otro. Un modelo afinado con documentos del
  proyecto A **no puede servir al proyecto B**, y un modelo no tiene cabecera
  `X-Project-Id`.
- **VRAM.** El pipeline ya pelea con esto: cada agente usa `keep_alive=0` para
  liberar memoria al terminar y un `num_ctx` fijo. Entrenar y servir en la misma
  máquina compiten por el mismo recurso escaso.
- **Resolución de modelo.** Hoy el modelo por agente sale de una cascada
  —`agent_settings` → `.agent.md` → default del proveedor—. Un modelo afinado es un
  cuarto origen que hay que colocar en esa cascada sin romperla.
- **¿Y cómo se sabe que mejoró?** Sin evaluación, «el modelo aprendió el estilo» es
  un acto de fe. La maquinaria para medirlo es la de E15, y hoy los datasets golden
  son `handwritten`: no distinguirían un fine-tune bueno de uno malo.

## Clarifications

### Session 2026-09-15

- Q: Si alguien pide borrar un documento que entró en un fine-tune, ¿cuál es la respuesta (retención)? → A: **No hay datos de usuario en ningún entrenamiento.** Solo se afina con un corpus **curado y con licencia** (papers de referencia, plantillas de estilo), documentado y versionado; los documentos que suben las personas usuarias nunca entran en unos pesos. La petición de supresión deja de afectar al modo fine-tune por construcción, y RAG sigue siendo la vía para documentos de usuario.
- Q: ¿A qué nivel existe un modelo afinado (alcance)? → A: **Uno por proyecto**, como mucho, y solo sirve a los agentes de ese proyecto. Respeta el aislamiento de T8.5; su lugar en la cascada de resolución de modelo lo fija el ADR (T19.2).
- Q: ¿Dónde se entrena (hardware)? → A: **Se decide tras el spike.** T19.1 mide en el hardware real de desarrollo (RTX 3070 Ti Laptop, 8 GB de VRAM) tiempo, VRAM pico y calidad; el ADR elige entre máquina aparte y la misma máquina en exclusiva con esos datos.
- Q: ¿Qué decide que un modelo afinado se adopta frente a RAG (criterio de éxito)? → A: **Métricas y revisión humana.** Debe superar a RAG en las métricas de E15 y en `format_compliance` sobre un dataset golden con `provenance: recorded` (no escrito a mano), **y** la comisión revisa salidas reales antes de adoptarlo. Depende de que E15 esté operativa.

## 3.0 Preguntas abiertas

Resueltas en [Clarifications](#clarifications): retención, alcance del modelo,
hardware (se decide con el spike) y criterio de éxito.

Quedan para el spike y el ADR, con una **propuesta de partida que T19.1 debe
confirmar o descartar**:

1. **Base y técnica.** Propuesta: adaptadores ligeros (LoRA o QLoRA) sobre un modelo
   base de la selección de E13 para el agente que más depende del formato (el
   formateador, `llama3.2:3b`), servidos por Ollama sin sustituir el modelo base. El
   número mínimo de ejemplos lo fija el spike: con dos documentos no se aprende
   estilo, se memoriza.
2. **Reversibilidad.** Propuesta: el modelo base nunca se modifica y el adaptador se
   versiona; retirarlo es quitarlo de la configuración del proyecto, con lo que la
   cascada vuelve al modelo del perfil y el modo vuelve a RAG **sin reentrenar**.

## 2. Objetivos / No-objetivos

- **Objetivos de esta fase:** medir la viabilidad real del fine-tune local (T19.1) y
  fijar su diseño en un ADR que respete las decisiones de Clarifications (T19.2).
- **No-objetivos de esta fase:** implementar entrenamiento, servir modelos afinados o
  activar el modo fine-tune en la interfaz (en T18.5 sigue apareciendo como no
  disponible); afinar con documentos de usuario, en esta ni en ninguna fase.

## 3. Criterios de aceptación (Given/When/Then)

- [ ] **AC1** — *Given* el hardware de desarrollo y un corpus curado de ejemplo con
  licencia documentada, *When* se ejecuta el spike con al menos un modelo base de la
  selección de E13 y una técnica de adaptación eficiente, *Then* un informe en
  `docs/reports/` registra tiempo de entrenamiento, VRAM pico, tamaño del artefacto
  resultante y una comparación de salidas frente a RAG sobre los mismos prompts; si no
  es viable en ese hardware, el informe lo dice con la cifra que lo impide.
- [ ] **AC2** — *Given* el spike, *Then* no se usa ningún documento subido por
  personas usuarias ni datos de producción: el corpus, su origen y su licencia quedan
  documentados en el informe, y el código del spike vive fuera de `backend/app`.
- [ ] **AC3** — *Given* el informe del spike, *When* se escribe el ADR, *Then* decide
  y justifica: que no hay datos de usuario en los entrenamientos, el alcance por
  proyecto y el lugar del modelo afinado en la cascada de resolución de modelo, dónde
  se entrena, base y técnica, el criterio de adopción (métricas de E15 y
  `format_compliance` sobre golden `recorded`, más revisión de la comisión) y cómo se
  vuelve a RAG sin reentrenar.
- [ ] **AC4** — *Given* el ADR aceptado, *Then* esta spec se amplía con los criterios
  y las tareas de implementación, y `data-retention.md` se actualiza si el diseño
  guarda pesos o adaptadores; *if* el ADR rechaza el fine-tune, *Then* la spec pasa a
  `Superseded` y T18.5 retira la opción de la interfaz.

## 4. Diseño propuesto

*El diseño lo fija el ADR (T19.2).* Lo que ya está decidido y **no** cambia:

- Sin datos de usuario en ningún entrenamiento (Clarifications).
- Como mucho un modelo afinado por proyecto (Clarifications).
- El modo fine-tune no puede saltarse el dispatcher único (`platform/llm.py`), ni el
  aislamiento por proyecto, ni la política de retención. Cualquier diseño que exija una
  excepción a los tres se descarta por esa razón.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Contenido de usuario atrapado en unos pesos | Irrecuperable ante una petición de supresión | Decidido: no hay datos de usuario en ningún entrenamiento (AC2, AC3) |
| Un modelo afinado cruza proyectos | Rompe T8.5 de la forma más difícil de detectar | Decidido: uno por proyecto; el ADR fija cómo lo aplica la cascada (AC3) |
| Entrenar deja la plataforma sin VRAM | Ejecuciones en curso degradadas o caídas | El spike mide antes de decidir dónde se entrena (AC1) |
| Se adopta sin poder medir si mejora | Complejidad permanente a cambio de nada demostrable | Criterio de adopción con métricas de E15, golden `recorded` y revisión humana (AC3) |
| El spike se convierte en implementación | Código de entrenamiento en producción sin ADR | El spike vive fuera de `backend/app` (AC2) y la implementación solo se planifica tras el ADR (AC4) |

## 6. Plan de pruebas

AC1 y AC2 se validan por el informe del spike: cifras presentes, corpus y licencia
documentados, y ningún archivo nuevo del spike bajo `backend/app`. AC3 por revisión del
ADR contra la lista del criterio. AC4 por la propia spec ampliada (o marcada
`Superseded`) tras aceptar o rechazar el ADR.

## 7. Impacto operativo / observabilidad

Ninguno en esta fase: ni código de producto ni cambios de esquema. Lo previsible tras el
ADR: almacenamiento de adaptadores, un ciclo de vida nuevo (entrenar / promover /
retirar) y una entrada en la política de retención.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E19
  title: "Aprendizaje de formato por fine-tune local"
  area: area/backend
tasks:
  - id: T19.1
    title: "Spike acotado: viabilidad en el hardware real (VRAM, tiempo, calidad)"
    sev: medium
    depends_on: []
    acceptance: [AC1, AC2]
  - id: T19.2
    title: "ADR de fine-tune local: retención, aislamiento, alcance y reversibilidad"
    sev: high
    depends_on: [T19.1]
    acceptance: [AC3, AC4]
```
