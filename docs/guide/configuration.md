# Configuración

La plataforma carga configuración con la siguiente prioridad (mayor a menor):

1. **Variables de entorno**
2. **`config.yaml`** (raíz del proyecto o `backend/`)
3. **Defaults** en `backend/app/core/config.py`

## Variables principales

| Variable | Default | Descripción |
|---|---|---|
| `SECRET_KEY` | — | **Obligatorio en producción.** Generar con `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | `postgresql+asyncpg://...` | URL de base de datos |
| `DEBUG` | `false` | Modo debug (activa hot-reload y admin auto-create) |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Orígenes CORS permitidos (coma-separados) |
| `LLM_PROVIDER` | `ollama` | Proveedor LLM: `ollama` o `openai` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL de Ollama |
| `OLLAMA_MODEL` | `llama3.2` | Modelo LLM por defecto |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Modelo de embeddings |
| `OPENAI_API_KEY` | — | API key de OpenAI (si `LLM_PROVIDER=openai`) |
| `OPENAI_MODEL` | `gpt-4o-mini` | Modelo OpenAI por defecto |
| `OPENAI_BASE_URL` | — | Override para Azure / Groq / vLLM |
| `QDRANT_URL` | `http://localhost:6333` | URL de Qdrant |
| `QDRANT_COLLECTION` | `rag_docs` | Colección RAG por defecto |
| `RAG_VECTOR_SIZE` | `768` | Dimensión del vector (768 para nomic-embed-text) |
| `ENABLE_DEV_ROLE_PROMOTION` | `false` | Permite auto-promoción de rol (solo dev) |
| `ENABLE_DEV_SEED` | `false` | Siembra usuarios de demo y contenido de ejemplo. Forzado a `false` si `DEBUG=false` |
| `DEV_ADMIN_PASSWORD` | `admin123` | Contraseña del admin sembrado (solo con `ENABLE_DEV_SEED`) |

::: warning Producción
`SECRET_KEY` no puede estar vacío ni usar valores por defecto en producción. El servidor rechazará el arranque si detecta un valor inseguro con `DEBUG=false`.
:::
