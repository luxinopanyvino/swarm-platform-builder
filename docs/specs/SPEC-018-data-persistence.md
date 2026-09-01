# SPEC-018: Datos y persistencia gestionados

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E4 (Datos y Persistencia)
- **ADR relacionado:** —
- **Severidad:** 🟡

> Adopta formalmente las tareas T4.1–T4.3 sembradas por el bootstrap sin spec.

## 1. Problema

El esquema evoluciona con `ALTER TABLE` caseros dentro de `try/except`
silenciosos en `init_db` (Alembic está en `requirements.txt` sin usarse); hay
un SQLite binario (`dev.db`) trackeado en git; y el estado de ejecución de los
pipelines (`active_streams`, `active_tasks`, `pending_decisions`) vive en la
memoria del proceso, lo que impide correr múltiples workers.

## 2. Objetivos / No-objetivos

- **Objetivos:** migraciones versionadas y reproducibles; repo sin artefactos
  binarios de BD; backend operable con N workers.
- **No-objetivos:** cambiar de motor de BD; alta disponibilidad de Redis.

## 3. Criterios de aceptación

- [x] **AC1** — *Given* un cambio de esquema, *When* se aplica, *Then* se hace
  mediante una migración **Alembic** versionada en el repo; `init_db` deja de
  ejecutar `ALTER TABLE` ad hoc y un despliegue limpio llega al mismo esquema
  que uno migrado.
- [x] **AC2** — *Given* el repo, *Then* `dev.db` (y cualquier `*.db` local) no
  está trackeado y `.gitignore` lo excluye; el arranque en dev lo recrea solo.
- [x] **AC3** — *Given* el backend con **más de un worker**, *When* un pipeline
  emite eventos SSE o espera una decisión HITL, *Then* streams/tareas/decisiones
  se coordinan vía Redis y cualquier worker puede atender la conexión, sin
  pérdida de eventos. *(hecho: #170, `test_bus_multiworker.py`)*

## 4. Diseño propuesto

AC1: `alembic init` + autogenerate contra los modelos de `app/models/`;
migración base desde el esquema actual. AC2: `git rm --cached` + `.gitignore`.
AC3: sustituir los dicts de proceso de
`modules/agents/application/use_cases.py` por estructuras Redis (pub/sub para
SSE, hash para decisiones), reutilizando `REDIS_URL` de la config; el ticket
store de SSE (SPEC-015/AC3) migra al mismo backend.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Divergencia esquema real ↔ primera migración | Alto | Migración base generada desde metadata + test de paridad |
| Redis como nueva dependencia dura en dev | Medio | Fallback en-proceso cuando `REDIS_URL` no está definido (single-worker) |

## 6. Plan de pruebas

Test de migración limpia vs. `create_all` (mismo esquema); test multi-worker
simulado (dos consumidores del bus Redis reciben los mismos eventos); CI sin
`dev.db`.

## 7. Impacto operativo / observabilidad

`alembic upgrade head` entra al flujo de despliegue; métricas de cola/bus en
T5.2 cuando exista.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E4
  title: "Datos y Persistencia"
  area: area/backend
tasks:
  - id: T4.1
    title: Adoptar Alembic (reemplazar ALTER caseros)
    sev: medium
    depends_on: []
    acceptance: [AC1]
  - id: T4.2
    title: Sacar dev.db de git + .gitignore
    sev: low
    depends_on: []
    acceptance: [AC2]
  - id: T4.3
    title: Externalizar estado en memoria a Redis (multi-worker)
    sev: medium
    depends_on: [T3.2]
    acceptance: [AC3]
```
