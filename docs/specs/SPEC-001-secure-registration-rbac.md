# SPEC-001: Registro seguro y RBAC de mínimo privilegio

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-06-26
- **Épica:** E1 (Identidad y Acceso)
- **ADR relacionado:** ADR-0003
- **Severidad:** 🔴

## 1. Problema

`register()` no asigna rol y `UserModel.role` tiene por defecto `REDACTOR`
([backend/app/routers/auth.py:35-39](../../backend/app/routers/auth.py#L35),
[backend/app/models.py:68](../../backend/app/models.py#L68)). Cualquier persona
que se registre obtiene de inmediato: creación de artículos, **ejecución de
pipelines de agentes, subida de ficheros al RAG y uso del scraper** (que además
tiene riesgo SSRF, ver SPEC-002). Es una escalada de privilegios por diseño.

## 2. Objetivos / No-objetivos

- **Objetivos:**
  - Rol por defecto de **mínimo privilegio** en el registro.
  - Promoción de rol controlada solo por administradores.
  - Desactivar/condicionar de forma segura los atajos de dev.
- **No-objetivos:** rediseñar todo el modelo RBAC ni añadir SSO (futuro).

## 3. Criterios de aceptación

- [ ] **AC1** — *Given* un usuario anónimo, *When* se registra vía
  `POST /api/v1/auth/register`, *Then* su rol es el de mínimo privilegio
  (`LECTOR` o `PUBLICO`, configurable) y **no** puede ejecutar pipelines, subir
  RAG ni invocar el scraper (403).
- [ ] **AC2** — *Given* un usuario no-admin, *When* intenta promover su rol,
  *Then* recibe 403; solo un `ADMIN` puede cambiar roles.
- [ ] **AC3** — *Given* `ENABLE_DEV_ROLE_PROMOTION` sin configurar, *Then* su
  valor efectivo es `False` (fail-safe) y el endpoint `dev/promote-reviewer`
  responde 403.
- [ ] **AC4** — Existen tests que cubren AC1–AC3.

## 4. Diseño propuesto

- Cambiar el default de `UserModel.role` a `LECTOR` **o** fijar el rol
  explícitamente en `register()` a partir de `settings.DEFAULT_SIGNUP_ROLE`
  (nuevo, default `lector`).
- Corregir el merge de configuración para que `ENABLE_DEV_ROLE_PROMOTION` tenga
  default `False` ([config.py:116](../../backend/app/core/config.py#L116)).
- Auditar endpoints que crean/ejecutan recursos para exigir rol `REDACTOR`/`ADMIN`.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Romper el onboarding actual (que esperaba REDACTOR) | Medio | Flag de configuración + nota de migración |
| Usuarios existentes con rol amplio | Medio | Script de revisión de roles (admin) |

## 6. Plan de pruebas

- Unit: registro → rol esperado; promoción no-admin → 403; flag dev off → 403.
- Integración: usuario recién registrado recibe 403 en `agents/{id}/run`,
  `rag/upload` y scraper.

## 7. Impacto operativo / observabilidad

- Log de auditoría en cambios de rol (épica E6).
- Documentar la variable `DEFAULT_SIGNUP_ROLE` en `.env.example`.
