---
name: publicador
model: null
temperature: null
rag_enabled: false
output_type: publication_result
focus: persistence
---

# Publicador

## Rol
Agente de publicación. Persiste el texto final en la base de datos, marca el artículo como `PUBLISHED` y genera los metadatos de indexación.

## Dominio
- Escritura en DB (PostgreSQL vía SQLAlchemy async)
- Generación de URL pública del artículo
- Cálculo de metadatos: word count, reading time, timestamp, licencia

## Sesgo
Determinismo total. No usa LLM. Opera directamente sobre la base de datos. Si el artículo no existe en DB, lo registra en logs pero no lanza excepción.

## Salida esperada
```json
{
  "published_url": "http://localhost:8080/articles/<id>/view",
  "metadata": {
    "indexed": true,
    "publisher": "AlejandrIA Magazine Editorial",
    "license": "CC-BY-4.0",
    "word_count": 1200,
    "reading_time_minutes": 6,
    "indexing_timestamp": "2026-05-29T..."
  }
}
```

## Cuándo invocarlo
Siempre como último nodo del flujo, tras el Formateador o el Revisor si no hay paso de formateo.
