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
Agente de publicación. Persiste el texto final en la base de datos, marca el artículo como `PUBLISHED`, genera los metadatos de indexación y produce la **maquetación tipo paper** (HTML imprimible) según el formato científico.

## Dominio
- Escritura en DB (PostgreSQL vía SQLAlchemy async)
- Generación de URL pública del artículo
- Cálculo de metadatos: word count, reading time, timestamp, licencia
- Maquetación determinista a HTML autocontenido (`paper_html`) con una plantilla por formato de cita (`apa`, `ieee`, `vancouver`, `chicago`, `nature`). IEEE se renderiza a 2 columnas; el resto a 1 columna con su convención visual. Ver `adapters/paper_layout.py`.

## Sesgo
Determinismo total. No usa LLM. Opera directamente sobre la base de datos. La maquetación se construye con un conversor markdown→HTML propio (sin dependencias). Si el artículo no existe en DB, lo registra en logs pero no lanza excepción. Si la maquetación falla, se registra y la publicación continúa.

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

Además, persiste `paper_html` en el artículo (recuperable vía `GET /api/v1/articles/<id>/paper`). El frontend lo muestra en `/articles/<id>/paper` con exportación a PDF desde el navegador.

```text
Nota: los metadatos del bloque de título (autores, afiliaciones, abstract)
se leen del artículo (campos authors[] y abstract). Si están vacíos, la
maquetación se genera igualmente con solo el título y el cuerpo.
```

## Cuándo invocarlo
Siempre como último nodo del flujo, tras el Formateador o el Revisor si no hay paso de formateo.
