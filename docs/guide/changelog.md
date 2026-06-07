# Changelog

## v0.1.0 — 2026-06-02

### Añadido
- Plataforma Agéntica Multiproyecto
- Proyecto de referencia: **AlejandrIA Magazine**
- Swarm de 5 agentes con LangGraph: investigador, redactor, revisor, formateador, publicador
- RAG con Qdrant 1.18 y embeddings `nomic-embed-text` (768 dim)
- Soporte multiproveedor LLM: Ollama y OpenAI/compatible
- Autenticación JWT con roles: admin, redactor, lector, publico
- Flow Designer visual para diseñar pipelines de agentes
- Biblioteca documental por proyecto con indexación paralela
- Streaming en tiempo real vía Server-Sent Events (SSE)
- API REST completa documentada en Swagger UI
- Script de arranque unificado para Windows (`dev-local.cmd`)
- Documentación con VitePress

### Seguridad
- CORS restringido a orígenes configurables (no más `*` con credenciales)
- Validación de tipo de token JWT (access vs refresh)
- Sanitización de nombres de colección RAG contra path traversal
- `SECRET_KEY` obligatorio en producción con validación al arranque
- `ENABLE_DEV_ROLE_PROMOTION` desactivado por defecto
