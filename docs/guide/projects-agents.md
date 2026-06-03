# Proyectos y agentes

## Crear un proyecto

Accede a **Proyectos → Nuevo proyecto** en la barra lateral. Elige el tipo de caso de uso y asigna un nombre. Al crear el proyecto, se provisionan automáticamente los agentes predefinidos para ese tipo.

## Tipos de agente

| Tipo | `is_builtin` | Descripción |
|---|---|---|
| **Integrado** | `true` | Preconfigurado por la plataforma. No puede borrarse, pero sí editarse. |
| **Personalizado** | `false` | Creado por el usuario. Editable y eliminable. |

El nombre de un agente debe ser único dentro del proyecto y usar solo letras minúsculas, números, guiones y guiones bajos.

## Campos configurables de un agente

| Campo | Tipo | Descripción |
|---|---|---|
| `name` / `slug` | string | Identificador único en el proyecto (ej: `mi-revisor`) |
| `model` | string | Modelo LLM (ej: `llama3.2:1b`, `gpt-4o-mini`) |
| `temperature` | float 0-1 | Creatividad de las respuestas |
| `prompt_template` | texto | Instrucciones de sistema para el agente |
| `rag_enabled` | bool | Activa la búsqueda en la base documental |
| `rag_collection` | string | Colección Qdrant sobre la que busca |
| `rag_chunk_size` | int 100–4000 | Tamaño de fragmento al indexar |
| `rag_chunk_overlap` | int 0–499 | Solapamiento entre fragmentos |
| `output_language` | string | Idioma de salida (`spanish`, `english`…) |
| `scientific_format` | enum | `apa` · `ieee` · `vancouver` · `none` |
| `target_word_count` | int | Extensión objetivo en palabras |
