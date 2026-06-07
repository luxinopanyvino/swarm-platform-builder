# Customizar y crear agentes

## Crear un agente desde la UI

1. Ve a **Agentes** dentro de tu proyecto.
2. Haz clic en **Nuevo agente**.
3. Rellena nombre (slug), descripción y elige el modelo LLM.
4. Configura RAG, prompt template y parámetros avanzados.
5. Guarda. El agente aparece disponible en el diseñador de flujos.

## Crear un agente desde la API

```bash
curl -X POST http://localhost:8000/api/v1/agents/claude-defs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<uuid-del-proyecto>",
    "name": "mi-agente",
    "description": "Agente especializado en resúmenes ejecutivos",
    "model": "llama3.2:1b",
    "temperature": 0.5,
    "rag_enabled": true,
    "rag_collection": "rag_docs",
    "prompt_template": "Eres un experto en síntesis científica. Responde siempre en español.",
    "output_language": "spanish",
    "target_word_count": 800
  }'
```

## Editar un agente existente

```bash
# Actualizar parámetros (enviar JSON con los campos a cambiar)
curl -X PUT http://localhost:8000/api/v1/agents/claude-defs/<agent-uuid> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "{\"temperature\": 0.3, \"target_word_count\": 1200}"
  }'

# Actualizar el prompt (enviar Markdown directamente)
curl -X PUT http://localhost:8000/api/v1/agents/claude-defs/<agent-uuid> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# Mi Agente\n\n## Rol\nExperto en síntesis..."
  }'
```

## Eliminar un agente

Solo los agentes **no integrados** pueden eliminarse:

```bash
curl -X DELETE http://localhost:8000/api/v1/agents/claude-defs/<agent-uuid> \
  -H "Authorization: Bearer <token>"
```

::: warning Agentes protegidos
Los agentes integrados del sistema (investigador, redactor, revisor, formateador, publicador, etc.) no pueden borrarse, pero sí modificarse.
:::

## Listar agentes de un proyecto

```bash
curl "http://localhost:8000/api/v1/agents/claude-defs?project_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```
