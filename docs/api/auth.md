# Autenticación API

Todos los endpoints protegidos requieren el header:

```
Authorization: Bearer <access_token>
```

## Registro

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "contraseña_segura",
    "full_name": "Nombre Apellido"
  }'
```

## Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "contraseña_segura"
  }'
# → { "access_token": "eyJ..." }
```

## Usuario actual

```bash
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer <token>"
```

## Gestión de usuarios (admin)

```bash
# Listar usuarios
curl http://localhost:8000/api/v1/auth/users \
  -H "Authorization: Bearer <admin_token>"

# Cambiar rol
curl -X PUT http://localhost:8000/api/v1/auth/users/<user_id>/role \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{ "role": "redactor" }'

# Asignar proyecto
curl -X PUT http://localhost:8000/api/v1/auth/users/<user_id>/project \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{ "project_id": "<uuid>" }'
```
