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

## Usuarios por defecto de desarrollo

Al arrancar en modo desarrollo, se crean automáticamente los siguientes usuarios:

> **Requieren flag explícito** (SPEC-015/T1.6). El arranque solo los siembra con
> `DEBUG=true` **y** `ENABLE_DEV_SEED=true`; `dev-local.cmd` ya los pone. Con
> `DEBUG=false` el flag se fuerza a `False` aunque `config.yaml` lo active, así que
> un despliegue de producción nunca crea estas cuentas.
>
> Se **crean si faltan** y no se reescriben: si cambias la contraseña del admin,
> sobrevive al reinicio.

**Admin**:
- **Email:** `admin@admin`
- **Contraseña:** `admin123`

**Redactor de Pruebas**:
- **Email:** `redactor@example.com`
- **Contraseña:** `redactor123`

**Revisor Académico**:
- **Email:** `revisor@example.com`
- **Contraseña:** `revisor123`

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
