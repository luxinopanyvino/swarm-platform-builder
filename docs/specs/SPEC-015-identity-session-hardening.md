# SPEC-015: Endurecimiento de identidad y sesiones (E1 resto)

- **Estado:** In progress
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E1 (Seguridad: Identidad y Acceso)
- **ADR relacionado:** ADR-0003
- **Severidad:** 🟠

> Adopta formalmente las tareas T1.2–T1.6 sembradas por el bootstrap
> (`seed_github_project.py`) que carecían de spec. T1.1 vive en
> [SPEC-001](SPEC-001-secure-registration-rbac.md). T1.2–T1.4 ya están
> implementadas y mergeadas (issues #154, #155, #156); sus AC se marcan como
> cumplidos con sus tests como evidencia.

## 1. Problema

Más allá del registro (SPEC-001), la gestión de sesiones y los atajos de dev
dejan huecos: sin protección de fuerza bruta, JWT sin revocación efectiva
(`jti` generado pero no verificado), token en el query string del SSE,
`ENABLE_DEV_ROLE_PROMOTION` activable por YAML en producción y seeds de
credenciales débiles (`admin123`, …) en cada arranque SQLite.

## 2. Objetivos / No-objetivos

- **Objetivos:** proteger login/registro contra fuerza bruta; revocación y
  refresh de JWT; SSE sin credenciales en URL; atajos de dev y seeds débiles
  imposibles en producción.
- **No-objetivos:** SSO/OIDC (épica futura); rediseño del modelo RBAC.

## 3. Criterios de aceptación

- [x] **AC1** — *Given* una IP que supera el umbral de intentos de
  login/registro, *When* reintenta dentro de la ventana, *Then* recibe `429`
  con `Retry-After`; y una cuenta con N fallos consecutivos queda bloqueada
  temporalmente (`423`). *(hecho: #154, `test_auth_rate_limit_lockout.py`)*
- [x] **AC2** — *Given* un token cuyo `jti` fue revocado (logout server-side),
  *When* se usa, *Then* la API responde `401`; el login emite además un
  refresh token y la renovación rota el par. *(hecho: #155)*
- [x] **AC3** — *Given* el stream SSE de ejecución, *When* un cliente conecta,
  *Then* se autentica con un **ticket efímero de un solo uso** y el JWT nunca
  viaja en el query string. *(hecho: #156, `test_sse_stream_ticket.py`)*
- [ ] **AC4** — *Given* `ENABLE_DEV_ROLE_PROMOTION` ausente **o** un
  `config.yaml` que lo activa, *When* `DEBUG=false`, *Then* el valor efectivo
  es `False` y `dev/promote-reviewer` responde `403`.
- [x] **AC5** — *Given* un arranque con `DEBUG=false`, *When* se inicializa la
  BD, *Then* **no** se siembran usuarios con credenciales débiles; el seed de
  demo solo corre bajo flag de dev explícito.
  *(hecho: #158, `test_dev_seed_flag.py`)*

## 4. Diseño propuesto

AC1–AC3 implementados (`app/core/rate_limit.py`, `app/core/stream_auth.py`,
revocación en `app/core/security.py`). AC4: forzar `False` salvo
`DEBUG=true` en `_build_settings`/`_validate_settings`
(`backend/app/core/config.py`). AC5: condicionar `ensure_dev_users()`
(`backend/app/main.py`) a un flag explícito de dev, nunca por defecto.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Lockout como vector de DoS contra una cuenta | Medio | Ventanas cortas + rate limit por IP previo |
| Entornos demo que dependían del seed | Bajo | Flag documentado en `.env.example` |

## 6. Plan de pruebas

Unit + e2e por AC (patrón de `backend/tests/test_auth_rate_limit_lockout.py` y
`test_sse_stream_ticket.py`); para AC4/AC5, tests de config con
`DEBUG=false` monkeypatched.

## 7. Impacto operativo / observabilidad

Logs de throttling/lockout ya emitidos (`app.auth`); documentar flags en
`.env.example`. Sin migraciones.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E1
  title: "Seguridad: Identidad y Acceso"
  area: area/security
tasks:
  - id: T1.2
    title: Rate limiting + bloqueo de cuenta en login/register
    sev: medium
    depends_on: []
    acceptance: [AC1]
  - id: T1.3
    title: Revocación de JWT (jti store/blacklist) + refresh token
    sev: medium
    depends_on: []
    acceptance: [AC2]
  - id: T1.4
    title: Sacar el token JWT del query string del SSE
    sev: high
    depends_on: []
    acceptance: [AC3]
  - id: T1.5
    title: ENABLE_DEV_ROLE_PROMOTION default False + gate prod
    sev: medium
    depends_on: []
    acceptance: [AC4]
  - id: T1.6
    title: Relegar seeds de credenciales débiles a flag de dev
    sev: medium
    depends_on: []
    acceptance: [AC5]
```
