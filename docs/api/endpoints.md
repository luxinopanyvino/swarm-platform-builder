# Endpoints

Documentación interactiva completa disponible en **http://localhost:8000/docs** (Swagger UI).

## Autenticación

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `POST` | `/api/v1/auth/register` | — | Registro de usuario |
| `POST` | `/api/v1/auth/login` | — | Login · devuelve JWT |
| `GET` | `/api/v1/auth/me` | ✓ | Usuario autenticado actual |
| `GET` | `/api/v1/auth/users` | admin | Listar usuarios |
| `PUT` | `/api/v1/auth/users/{id}/role` | admin | Cambiar rol de usuario |
| `PUT` | `/api/v1/auth/users/{id}/project` | admin | Asignar proyecto a usuario |

## Proyectos

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/projects` | ✓ | Listar proyectos visibles al usuario |
| `POST` | `/api/v1/projects` | ✓ | Crear proyecto |
| `GET` | `/api/v1/projects/{id}` | ✓ | Detalle de proyecto |
| `DELETE` | `/api/v1/projects/{id}` | admin | Eliminar proyecto |

## Artículos

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/articles` | ✓ | Listar artículos |
| `POST` | `/api/v1/articles` | ✓ | Crear borrador |
| `GET` | `/api/v1/articles/{id}` | ✓ | Obtener artículo |
| `PUT` | `/api/v1/articles/{id}` | ✓ | Actualizar artículo |
| `POST` | `/api/v1/articles/{id}/submit` | ✓ | Enviar a revisión |
| `POST` | `/api/v1/articles/{id}/approve` | admin | Aprobar |
| `POST` | `/api/v1/articles/{id}/reject` | admin | Rechazar |

## Agentes

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/agents/claude-defs` | ✓ | Listar perfiles de agentes del proyecto |
| `POST` | `/api/v1/agents/claude-defs` | ✓ | Crear agente personalizado |
| `PUT` | `/api/v1/agents/claude-defs/{id}` | ✓ | Editar agente |
| `DELETE` | `/api/v1/agents/claude-defs/{id}` | ✓ | Eliminar agente (no integrados) |
| `GET` | `/api/v1/agents/models` | ✓ | Modelos LLM disponibles |
| `POST` | `/api/v1/agents/{article_id}/run` | ✓ | Lanzar pipeline |
| `GET` | `/api/v1/agents/{article_id}/runs` | ✓ | Historial de ejecuciones |
| `GET` | `/api/v1/agents/{article_id}/stream` | ✓ | Stream SSE en tiempo real |

## RAG / Biblioteca

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/agents/rag/library` | ✓ | Listar documentos indexados |
| `POST` | `/api/v1/agents/rag/library/upload` | ✓ | Subir documento |
| `DELETE` | `/api/v1/agents/rag/library/{col}/{doc_id}` | ✓ | Eliminar documento |
| `POST` | `/api/v1/agents/{agent}/rag/upload` | ✓ | Subir doc a agente específico |

## Flujos

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/flows` | ✓ | Listar flujos guardados |
| `POST` | `/api/v1/flows` | ✓ | Guardar nuevo flujo |
| `PUT` | `/api/v1/flows/{id}` | ✓ | Actualizar flujo |
| `DELETE` | `/api/v1/flows/{id}` | ✓ | Eliminar flujo |

## AI / LLM

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/ai/models` | ✓ | Listar modelos disponibles |
| `POST` | `/api/v1/ai/assist` | ✓ | Asistencia IA sobre texto |
| `POST` | `/api/v1/ai/format` | ✓ | Formatear texto científico |

## Revista pública

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/magazine` | — | Artículos publicados (sin auth) |

## Configuración (admin)

| Método | Ruta | Auth | Descripción |
|---|---|:---:|---|
| `GET` | `/api/v1/config` | ✓ | Leer config.yaml |
| `PUT` | `/api/v1/config` | admin | Actualizar config.yaml |
