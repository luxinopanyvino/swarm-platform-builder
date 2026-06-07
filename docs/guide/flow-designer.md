# Diseñador de flujos

El **Flow Designer** es el editor visual donde conectas agentes para construir pipelines.

## Cómo usarlo

1. Accede a **Flujos** dentro de tu proyecto.
2. Los agentes del proyecto aparecen como **nodos arrastrables** en el panel izquierdo.
3. Arrastra los agentes al canvas y **conecta sus salidas y entradas** en el orden deseado.
4. Guarda el flujo con un nombre. Podrás reutilizarlo en múltiples ejecuciones.

## Ejemplo de flujo completo (AlejandrIA Magazine)

```
investigador → redactor → revisor → formateador → publicador
```

## Flujos parciales

Puedes ejecutar solo una parte del pipeline:

```
# Solo revisar y reformatear un borrador existente
revisor → formateador → publicador

# Solo redactar sin investigación previa
redactor → revisor → formateador → publicador
```

## Estado compartido entre agentes (`AgentState`)

Todos los agentes de un flujo comparten un estado acumulado:

```python
class AgentState(TypedDict):
    article_id: UUID
    author_id: UUID
    title: str
    keywords: list[str]
    research_data: str       # contexto del Investigador
    sources: list[dict]      # fuentes encontradas
    draft_text: str          # borrador del Redactor
    feedback: list[str]      # comentarios del Revisor
    approval_score: float    # puntuación 0-100
    formatted_text: str      # texto del Formateador
    scientific_format: str   # "apa" | "ieee" | "vancouver"
    published_url: str       # URL final
    flow_sequence: list[str] # secuencia de nodos
    loop_count: int          # iteraciones del bucle Revisor → Redactor
```

Cada ejecución queda registrada en la tabla `agent_runs` para trazabilidad completa.
