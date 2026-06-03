# RAG API

## Subir documento a la biblioteca

```bash
curl -X POST http://localhost:8000/api/v1/agents/rag/library/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@paper.pdf" \
  -F "collection=biblioteca" \
  -F "chunk_size=500" \
  -F "chunk_overlap=50"
```

Respuesta:

```json
{
  "status": "indexed",
  "doc_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "paper.pdf",
  "collection": "biblioteca",
  "chunks": 42
}
```

## Listar documentos indexados

```bash
curl http://localhost:8000/api/v1/agents/rag/library \
  -H "Authorization: Bearer <token>"
```

## Eliminar documento

```bash
curl -X DELETE \
  "http://localhost:8000/api/v1/agents/rag/library/biblioteca/<doc_id>" \
  -H "Authorization: Bearer <token>"
```

## Subir documento a un agente específico

```bash
curl -X POST "http://localhost:8000/api/v1/agents/investigador/rag/upload" \
  -H "Authorization: Bearer <token>" \
  -F "file=@fuentes.txt" \
  -F "rag_collection=rag_docs"
```
