# ADR-0012: Fine-tune local para aprender formato, acotado y reversible

- **Estado:** Propuesto
- **Fecha:** 2026-10-22
- **Decisores:** Equipo de plataforma
- **Specs relacionadas:** [SPEC-031](../specs/SPEC-031-format-learning-finetune.md) (T19.2)
- **Origen:** la maqueta de subida ofrece «RAG» y «fine-tune» como modos equivalentes; solo existe RAG.

## Contexto

RAG se puede deshacer: borrar un documento retira su influencia en la siguiente recuperación. Un
fine-tune no: lo que entra en un entrenamiento queda **dentro de los pesos** y borrarlo exige
reentrenar, suponiendo que se sepa qué entró. Eso choca con
[data-retention.md](../governance/data-retention.md) y con cualquier petición de supresión. Además:
el aislamiento por proyecto (T8.5) no tiene equivalente en un modelo, que no lleva `X-Project-Id`;
entrenar y servir compiten por la VRAM que el pipeline ya gestiona con `keep_alive=0`; el modelo
por agente sale de una cascada (`resolve_agent_model`) en la que un modelo afinado sería un origen
nuevo; y sin evaluación «aprendió el estilo» es un acto de fe (los golden de E15 son hoy `handwritten`).

## Decisión

Las cuatro decisiones de política están tomadas (SPEC-031, *Clarifications* del 2026-09-15) y este
ADR las fija; lo que depende de medir queda explícitamente abierto.

**Decidido**

1. **Ningún dato de usuario entra en un entrenamiento.** Solo un corpus **curado y con licencia**
   (papers de referencia, plantillas de estilo), documentado y versionado. Los documentos que suben
   las personas usuarias siguen en RAG. La supresión no afecta al fine-tune por construcción.
2. **Como mucho un modelo afinado por proyecto**, que solo sirve a los agentes de ese proyecto.
3. **Lugar en la cascada de modelo:** `agent_settings` (lo explícito de la ejecución gana) →
   **modelo afinado del proyecto, si está promovido y el agente lo declara** → `.agent.md` → default del
   proveedor. Retirarlo es quitarlo de la configuración del proyecto: la cascada vuelve sola al
   modelo del perfil y el modo vuelve a RAG **sin reentrenar**.
4. **Reversibilidad:** el modelo base nunca se modifica; el artefacto es un adaptador versionado
   (LoRA/QLoRA) servido junto al base, no un modelo nuevo mezclado.
5. **Sin excepciones:** el modo fine-tune no se salta el dispatcher único (`platform/llm.py`), el
   aislamiento por proyecto ni la política de retención. Un diseño que exija una excepción a
   cualquiera de los tres se descarta.
6. **Criterio de adopción frente a RAG:** superar a RAG en las métricas de E15 y en
   `format_compliance` sobre un golden con `provenance: recorded` (no escrito a mano), **y** revisión
   de salidas reales por la comisión. Hasta que E15 tenga golden `recorded`, no se adopta.

**Abierto, a confirmar por el spike (T19.1)**

- **Dónde se entrena** (máquina aparte o la misma en exclusiva): lo decide la medición en el hardware
  de desarrollo (RTX 3070 Ti Laptop, 8 GB): tiempo, VRAM pico y calidad.
- **Base y técnica concretas:** propuesta de partida, adaptadores ligeros sobre el modelo del agente más
  dependiente del formato (el formateador, `llama3.2:3b`), servidos por Ollama. El número mínimo de
  ejemplos lo fija el spike: con dos documentos no se aprende estilo, se memoriza.

## Consecuencias

- **Positivas:** la política de retención no se debilita; el modo se puede retirar sin coste; el aislamiento
  se conserva; la adopción exige evidencia en vez de fe.
- **Negativas:** el valor depende de curar un corpus con licencia y de tener un golden `recorded`, trabajo
  que hoy no existe; cada proyecto que lo quiera carga con su adaptador.
- **No se hace en esta fase:** código de entrenamiento en `backend/app`, servir modelos afinados ni activar
  el modo en la interfaz (sigue como no disponible, T18.5). Esas tareas se añaden a SPEC-031 cuando este ADR
  pase a `Aceptado` y el spike confirme la viabilidad; si el spike la descarta, la spec pasa a `Superseded` y
  T18.5 retira la opción.

## Alternativas descartadas

- **Afinar también con documentos de usuario:** irrecuperable ante una supresión; rompe la retención.
- **Un modelo compartido por todos los proyectos:** rompe el aislamiento de T8.5 de la forma más difícil de detectar.
- **Sustituir el modelo base por uno afinado fusionado:** impide volver a RAG sin reentrenar.
