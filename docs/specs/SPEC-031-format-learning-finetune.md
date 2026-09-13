# SPEC-031: Aprendizaje de formato por fine-tune local

- **Estado:** Draft
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-09-13
- **Épica:** E19 (GitHub Project)
- **ADR relacionado:** ADR pendiente — es **prerrequisito**, no consecuencia
- **Severidad:** 🟠

> **Esta spec está en `Draft` a propósito y no genera issues.** No es un descuido
> del flujo: es que las preguntas de la sección 3.0 no tienen respuesta todavía, y
> sembrar tareas sobre una decisión no tomada es cómo se construyen features a
> medias. Pasa a `Ready` cuando el ADR exista.

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

A eso se suman cuatro cosas que hoy no tienen respuesta y que no son detalles de
implementación:

- **Aislamiento por proyecto.** T8.5 costó construirlo: la colección se deriva y un
  perfil no puede apuntar al espacio de otro. Un modelo afinado con documentos del
  proyecto A **no puede servir al proyecto B**, y un modelo no tiene cabecera
  `X-Project-Id`. ¿Un modelo por proyecto? ¿Por artículo?
- **VRAM.** El pipeline ya pelea con esto: cada agente usa `keep_alive=0` para
  liberar memoria al terminar y un `num_ctx` fijo. Entrenar y servir en la misma
  máquina compiten por el mismo recurso escaso.
- **Resolución de modelo.** Hoy el modelo por agente sale de una cascada
  —`agent_settings` → `.agent.md` → default del proveedor—. Un modelo afinado es un
  cuarto origen que hay que colocar en esa cascada sin romperla.
- **¿Y cómo se sabe que mejoró?** Sin evaluación, «el modelo aprendió el estilo» es
  un acto de fe. La maquinaria para medirlo es justo la de E15, y hoy los datasets
  golden son `handwritten`: no distinguirían un fine-tune bueno de uno malo.

## 2. Objetivos / No-objetivos

- **Objetivo de esta spec en `Draft`:** dejar escritas las preguntas que hay que
  responder y el orden en que responderlas, para que la decisión se tome una vez y
  con criterio.
- **No-objetivo:** implementar nada antes del ADR.

## 3.0 Preguntas abiertas (pendientes de `/speckit-clarify`)

1. **Retención.** Si un usuario pide borrar un documento que entró en un
   entrenamiento, ¿cuál es la respuesta? (Reentrenar, retirar el modelo, o no
   ofrecer fine-tune sobre documentos de usuario.)
2. **Alcance del modelo.** ¿Uno por proyecto, por agente, por artículo? ¿Quién
   puede lanzarlo y quién puede usarlo?
3. **Hardware.** ¿Entrena en la misma máquina que sirve? ¿Con qué presupuesto de
   VRAM y tiempo, y qué pasa con las ejecuciones en curso mientras tanto?
4. **Base y técnica.** ¿Sobre qué modelo, con qué método (LoRA u otro), con cuántos
   ejemplos mínimos? Un «aprende el estilo desde múltiples ejemplos» con dos
   documentos no aprende estilo: memoriza.
5. **Criterio de éxito.** ¿Qué métrica decide que el fine-tune se adopta frente al
   RAG, y quién la mide? (Depende de E15.)
6. **Reversibilidad.** ¿Cómo se vuelve atrás si el modelo afinado resulta peor?

## 3. Criterios de aceptación

*Pendientes: se escriben cuando las preguntas de 3.0 tengan respuesta. Redactarlos
antes sería fijar como verificable algo que aún no está decidido.*

## 4. Diseño propuesto

*Pendiente del ADR.* Lo único ya decidido es lo que **no** cambia: el modo
fine-tune no puede saltarse el dispatcher único (`platform/llm.py`), ni el
aislamiento por proyecto, ni la política de retención. Cualquier diseño que exija
una excepción a los tres debería descartarse por esa razón.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Se implementa antes de decidir la retención | Contenido de usuario irrecuperable dentro de unos pesos | Esta spec en `Draft`: sin ADR no hay tareas |
| Un modelo afinado cruza proyectos | Rompe T8.5 de la forma más difícil de detectar | Pregunta 2, antes de escribir código |
| Entrenar deja la plataforma sin VRAM | Ejecuciones en curso degradadas o caídas | Pregunta 3 |
| Se adopta sin poder medir si mejora | Complejidad permanente a cambio de nada demostrable | Pregunta 5; depende de E15 |

## 6. Plan de pruebas

*Pendiente.*

## 7. Impacto operativo / observabilidad

*Pendiente.* Lo previsible: almacenamiento de pesos, un ciclo de vida nuevo
(entrenar / promover / retirar) y una entrada en la política de retención.

## 8. Backlog (sincronización SDD)

> Las specs en `Draft` **no se sincronizan**: este bloque describe el trabajo que
> existiría si el ADR sale adelante, y no crea issues hasta que la spec pase a
> `Ready`.

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
    acceptance: []
  - id: T19.2
    title: "ADR de fine-tune local: retención, aislamiento, alcance y reversibilidad"
    sev: high
    depends_on: [T19.1]
    acceptance: []
```
