# Agentes API

## Listar agentes de un proyecto

```bash
curl "http://localhost:8000/api/v1/agents/claude-defs?project_id=<uuid>" \
  -H "Authorization: Bearer <token>"
```

## Crear agente

```bash
curl -X POST http://localhost:8000/api/v1/agents/claude-defs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "<uuid>",
    "name": "sintetizador",
    "description": "Crea resúmenes ejecutivos de artículos científicos",
    "model": "llama3.2:1b",
    "temperature": 0.4,
    "rag_enabled": true,
    "rag_collection": "rag_docs",
    "output_language": "spanish",
    "target_word_count": 600
  }'
```

## Lanzar pipeline

```bash
curl -X POST http://localhost:8000/api/v1/agents/{article_id}/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_sequence": ["investigador", "redactor", "revisor", "formateador", "publicador"],
    "keywords": ["inteligencia artificial", "revisión sistemática"],
    "context_description": "Artículo para revista de tecnología aplicada",
    "agent_settings": {
      "redactor": {
        "model": "mistral",
        "temperature": 0.7,
        "output_language": "spanish",
        "target_word_count": 2000
      },
      "formateador": {
        "scientific_format": "apa"
      }
    }
  }'
```

## Escuchar eventos SSE en tiempo real

```bash
curl -N http://localhost:8000/api/v1/agents/{article_id}/stream \
  -H "Authorization: Bearer <token>"
```

Cada evento tiene el formato:

```
data: {"agent": "redactor", "event": "chunk", "content": "..."}
data: {"agent": "redactor", "event": "done", "tokens": 1240}
```

## Historial de ejecuciones

```bash
curl http://localhost:8000/api/v1/agents/{article_id}/runs \
  -H "Authorization: Bearer <token>"
```
