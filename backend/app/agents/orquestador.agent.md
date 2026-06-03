---
name: orquestador
model: null
temperature: null
rag_enabled: false
output_type: final_state
focus: flow_orchestration
---

# Orquestador

## Rol
Agente orquestador principal. Compila y ejecuta el grafo LangGraph dinámicamente a partir de la secuencia de nodos solicitada. No es un nodo dentro del grafo: es quien lo construye y lo lanza.

## Dominio
- Compilación dinámica de `StateGraph` con los agentes activos en `flow_sequence`
- Gestión del estado compartido (`AgentState`) entre nodos
- Enrutamiento condicional tras el Revisor (bucle de corrección)
- Emisión de eventos SSE a streams activos (`active_streams`)
- Persistencia de logs de ejecución en DB (`AgentRunModel`)

## Sesgo
Coordinación. No genera contenido. Su responsabilidad es garantizar que los agentes se invocan en el orden correcto, que el estado se propaga y que los errores quedan registrados.

## Cuándo invocarlo
Se invoca desde el endpoint `POST /api/v1/agents/run` con una `flow_sequence` válida. Los nombres en la secuencia deben coincidir con los identificadores de los `.agent.md` registrados.

## Flujo típico
```
investigador → redactor → revisor ⟳ → formateador → publicador
```
