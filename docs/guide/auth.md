# Autenticación y roles

## Roles de usuario

| Rol | Permisos |
|---|---|
| **admin** | Gestión completa: usuarios, proyectos, agentes, aprobar/rechazar artículos |
| **redactor** | Crear y editar artículos, ejecutar pipelines, ver todos los artículos del proyecto |
| **lector** | Solo lectura del proyecto que le asigne el admin |
| **publico** | Solo el endpoint público de la revista (sin autenticación) |

## Tokens JWT

- Los tokens de **acceso** expiran a los 30 minutos (configurable con `ACCESS_TOKEN_EXPIRE_MINUTES`).
- Los tokens de **refresco** expiran a los 7 días.
- Un token de refresco **no puede usarse** como token de acceso (validación por campo `type`).

## Usuario administrador de desarrollo

Al arrancar con SQLite (`DEBUG=true`), se crea automáticamente:

- **Email:** `admin@admin`
- **Contraseña:** configurable con `DEV_ADMIN_PASSWORD` (por defecto `admin123`)

::: danger
No usar credenciales de desarrollo en producción. Cambiar `SECRET_KEY` y la contraseña de admin antes de cualquier despliegue.
:::

## Endpoints de autenticación

```bash
# Registro
POST /api/v1/auth/register
{ "email": "...", "password": "...", "full_name": "..." }

# Login
POST /api/v1/auth/login
{ "email": "...", "password": "..." }
# → { "access_token": "..." }

# Usuario actual
GET /api/v1/auth/me
Authorization: Bearer <token>
```
