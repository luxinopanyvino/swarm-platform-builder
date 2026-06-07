# Flujo de redacción de papers

## Diagrama del pipeline

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  🔍 INVESTIGADOR                    │
│  Qdrant RAG + EuropePMC + OpenAlex  │
└──────────────────┬──────────────────┘
                   │ research_data + sources
                   ▼
┌─────────────────────────────────────┐
│  ✍️  REDACTOR                       │
│  Genera borrador Markdown           │◄──────────────┐
└──────────────────┬──────────────────┘               │
                   │ draft_text                        │ feedback
                   ▼                                   │ (score < 80)
┌─────────────────────────────────────┐               │
│  🧐 REVISOR                         │───────────────┘
│  Score 0-100 · max 3 iteraciones    │
└──────────────────┬──────────────────┘
                   │ score ≥ 80
                   ▼
┌─────────────────────────────────────┐
│  📐 FORMATEADOR                     │
│  APA / IEEE / Vancouver             │
└──────────────────┬──────────────────┘
                   │ formatted_text
                   ▼
┌─────────────────────────────────────┐
│  📢 PUBLICADOR                      │
│  DB update → status: PUBLISHED      │
└──────────────────┬──────────────────┘
                   │
                  END
```

## Paso a paso desde la UI

1. Crea un artículo en **Artículos → Nuevo artículo** (título y palabras clave).
2. En el detalle del artículo, haz clic en **Ejecutar pipeline**.
3. Selecciona los agentes que quieres incluir y el orden.
4. Haz clic en **Lanzar**. Los resultados aparecen en tiempo real en el panel de ejecución.

## Ejecutar desde la API

```bash
curl -X POST http://localhost:8000/api/v1/agents/{article_id}/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "flow_sequence": ["investigador", "redactor", "revisor", "formateador", "publicador"],
    "keywords": ["machine learning", "climate change"],
    "context_description": "Artículo para revista de inteligencia artificial aplicada"
  }'
```

## Flujos parciales comunes

| Objetivo | Secuencia |
|---|---|
| Pipeline completo | `investigador → redactor → revisor → formateador → publicador` |
| Solo redactar (sin investigar) | `redactor → revisor → formateador → publicador` |
| Repasar y publicar un borrador | `revisor → formateador → publicador` |
| Solo formatear | `formateador → publicador` |

## Estado del artículo

```
DRAFT ──submit──► IN_REVIEW ──approve──► PUBLISHED
                      │
                   reject
                      │
                      ▼
                    DRAFT  (con comentario de revisión)
```

| Estado | Descripción |
|---|---|
| `draft` | Borrador, editable por el autor |
| `in_review` | Enviado a revisión humana |
| `published` | Aprobado y visible en la revista |
| `rejected` | Rechazado, vuelve a borrador con comentario |
