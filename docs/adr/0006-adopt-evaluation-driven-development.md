# ADR-0006: Adoptar Evaluation-Driven Development (EDD) para los agentes de la plataforma

- **Estado:** Propuesto
- **Fecha:** 2026-06-30
- **Decisores:** Equipo de plataforma
- **Specs relacionadas:** [SPEC-014](../specs/SPEC-014-explainability-and-edd.md) · complementa [ADR-0004](0004-observability-and-ci.md)

## Contexto

El comportamiento de los agentes del pipeline depende de artefactos fácilmente
mutables: `prompt_template`, `model`, `temperature` y los `*.agent.md`. Hoy un
cambio en cualquiera de ellos puede **degradar la calidad sin que nada lo
detecte**: no hay datasets de referencia, métricas de comportamiento ni un gate de
regresión. La calidad se valora a ojo, ejecución a ejecución.

SDD ([ADR-0002](0002-adopt-spec-driven-development.md)) gobierna *qué* se construye;
falta una disciplina equivalente que gobierne *cómo de bien se comporta* lo
construido, específicamente para componentes probabilísticos (LLM/agentes).

## Decisión

Adoptaremos **Evaluation-Driven Development (EDD)** como disciplina de primer
nivel, acotada al **comportamiento de los agentes y modelos configurados en la
plataforma** (no a modelos *foundation* globales ni a *benchmarking* de
proveedores):

1. **Evals como artefacto versionado.** Datasets *golden* y métricas de
   comportamiento viven en el repo (`backend/evals/`), junto al código que evalúan.
2. **Métricas de comportamiento** por agente: fidelidad de citas, cumplimiento de
   formato, calibración del Revisor, coherencia y presupuesto de tokens/latencia.
   Se priorizan las deterministas; el *LLM-as-judge*, cuando se use, es un **modelo
   de la plataforma** con rúbrica y `temperature=0`.
3. **Gate de regresión en CI** para PRs que tocan agentes/modelos, con umbrales
   declarados; arranca en modo **aviso** y se endurece tras fijar la línea base.
4. **Área de gobernanza propia** `area/evaluation`, con su épica (E9) y su flujo
   SDD (spec → `/sdd-sync` → `/resolve-task`), análogo al resto de áreas.

EDD se apoya en la **explicabilidad** (SPEC-014): la traza por paso es el sustrato
de datos que alimenta las evals.

## Alternativas consideradas

- **Solo revisión humana / QA manual** — no escala, no es reproducible y no detecta
  regresiones sutiles entre versiones de *prompt*/modelo.
- **Servicio SaaS de evaluación de LLMs** — coste, dependencia externa y, sobre
  todo, **fuera de alcance**: evaluaría modelos genéricos, no el comportamiento de
  *nuestros* agentes sobre *nuestros* datos. Empezamos con harness propio on-prem,
  coherente con el stack (Ollama/OpenAI configurables).
- **Tests unitarios clásicos únicamente** — insuficientes para salidas
  probabilísticas; se complementan con métricas y rúbricas, no se sustituyen.

## Consecuencias

- **Positivas:** detección temprana de regresiones de calidad, desarrollo de
  agentes guiado por datos, reproducibilidad, y sinergia con observabilidad (los
  scores se publican como métricas) y explicabilidad (traza auditable).
- **Negativas / coste:** cómputo de evals en CI (mitigado con datasets pequeños y
  *gate* selectivo), curación de datasets *golden*, y calibración de umbrales.
- **Seguimiento:** épica **E9** (`area/evaluation`); implementación en
  [SPEC-014](../specs/SPEC-014-explainability-and-edd.md).
