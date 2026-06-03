# Base documental RAG

La plataforma incluye una **biblioteca documental** por colección. Los agentes con `rag_enabled = true` buscan automáticamente en ella durante la ejecución.

## Subir documentos

**Formatos admitidos:** `.txt`, `.md`, `.pdf` (máx. 10 MB por archivo).

### Desde la UI

1. Accede a **Biblioteca** en el menú del proyecto.
2. Arrastra o selecciona el archivo y haz clic en **Subir**.
3. El documento se divide en fragmentos (chunks), se vectoriza con `nomic-embed-text` y se indexa en Qdrant.

### Desde la API

```bash
curl -X POST http://localhost:8000/api/v1/agents/rag/library/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@mi-paper.pdf" \
  -F "collection=biblioteca"
```

## Parámetros de indexación

| Parámetro | Default | Descripción |
|---|---|---|
| `collection` | `biblioteca` | Colección Qdrant destino |
| `chunk_size` | `500` | Caracteres por fragmento |
| `chunk_overlap` | `50` | Solapamiento entre fragmentos |

## Estructura interna en Qdrant

```
Qdrant
└── colección: biblioteca
    ├── punto UUID (chunk 1)
    │   ├── vector: [768 floats]   ← nomic-embed-text
    │   └── payload: { doc_id, filename, agent_name, text }
    └── punto UUID (chunk 2) ...
```

## Eliminar un documento

```bash
curl -X DELETE \
  "http://localhost:8000/api/v1/agents/rag/library/biblioteca/<doc_id>" \
  -H "Authorization: Bearer <token>"
```
