# SPEC-017: Infraestructura y despliegue endurecidos

- **Estado:** In progress
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E3 (Infraestructura y Despliegue)
- **ADR relacionado:** ADR-0003
- **Severidad:** 🟠

> Adopta formalmente las tareas T3.1–T3.5 sembradas por el bootstrap sin spec.
> T3.1 y T3.2 ya están implementadas y mergeadas (issues #163, #164); sus AC se
> marcan cumplidos con sus tests y bitácoras como evidencia.

## 1. Problema

El despliegue Docker exponía servicios internos sin autenticación (Qdrant
`:6333`, Ollama `:11434`, Postgres `:5432`), llevaba secretos hardcodeados en
git, ejecuta contenedores como root con toolchain de build en la imagen final,
mezcla dev y prod en un único compose (`--reload`, sin TLS ni cabeceras) y
carece de límites de recursos (Ollama puede agotar RAM/VRAM del host).

## 2. Objetivos / No-objetivos

- **Objetivos:** servicios internos autenticados y no publicados; secretos solo
  por entorno con rotación; contenedores mínimos y sin privilegios; despliegue
  prod separado de dev con TLS/cabeceras; recursos acotados.
- **No-objetivos:** orquestación más allá de docker-compose (k8s); gestor de
  secretos externo (Vault) — se documenta como evolución.

## 3. Criterios de aceptación

- [x] **AC1** — *Given* el `docker-compose`, *Then* Qdrant exige API key en
  cada petición y `qdrant`/`ollama`/`postgres` **no** publican puertos al host
  (solo la red interna); únicamente `backend` y `frontend` quedan expuestos.
  *(hecho: #163, `test_qdrant_auth.py`)*
- [x] **AC2** — *Given* el repo, *Then* no hay credenciales hardcodeadas en el
  compose (guardas `${VAR:?}`), la rotación está documentada y un `SECRET_KEY`
  placeholder o corto **no** pasa la validación de arranque en producción.
  *(hecho: #164, `test_config_secret_validation.py`)*
- [ ] **AC3** — *Given* las imágenes, *When* se construyen, *Then* los
  contenedores corren con `USER` no root y la imagen final del backend no
  incluye `build-essential` ni toolchain de compilación.
- [ ] **AC4** — *Given* el despliegue, *Then* existen compose **dev y prod
  separados** (prod sin `--reload` ni `DEBUG`), y nginx sirve con TLS y
  cabeceras de seguridad + CSP.
- [ ] **AC5** — *Given* los servicios del compose, *Then* declaran límites de
  recursos (memoria/CPU donde aplique) y healthchecks de **readiness** además
  de liveness.

## 4. Diseño propuesto

AC3: multi-stage build en `backend/Dockerfile` + `USER app`. AC4:
`docker-compose.yml` (dev) + `docker-compose.prod.yml` (override) y bloque de
cabeceras/CSP en la conf de nginx del frontend (la CSP cubre el iframe de
SPEC-016/AC1). AC5: `deploy.resources.limits`/`mem_limit` + healthchecks con
umbrales por servicio.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Imagen slim rompe deps con extensiones nativas | Medio | Multi-stage: compilar en builder, copiar wheels |
| Límites demasiado bajos matan a Ollama | Medio | Medir consumo real antes de fijar límites |

## 6. Plan de pruebas

`docker compose config` en CI (guardas e interpolación); inspección de imagen
(`USER`, ausencia de toolchain); smoke test de cabeceras nginx (`curl -I`).

## 7. Impacto operativo / observabilidad

Cambia el flujo de despliegue (variables obligatorias, compose prod). Rotación
de secretos documentada en `SECURITY.md`.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E3
  title: "Infraestructura y Despliegue"
  area: area/infra
tasks:
  - id: T3.1
    title: Autenticar Qdrant (API key) y no exponer puertos internos
    sev: high
    depends_on: []
    acceptance: [AC1]
  - id: T3.2
    title: Gestión de secretos fuera de git + rotación
    sev: high
    depends_on: []
    acceptance: [AC2]
  - id: T3.3
    title: Contenedores no-root + imagen backend slim
    sev: medium
    depends_on: []
    acceptance: [AC3]
  - id: T3.4
    title: Compose dev/prod separados; TLS; cabeceras + CSP en nginx
    sev: medium
    depends_on: [T3.1, T3.2]
    acceptance: [AC4]
  - id: T3.5
    title: Límites de recursos + healthchecks de readiness
    sev: low
    depends_on: []
    acceptance: [AC5]
```
