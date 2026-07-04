# Gobernanza del proyecto

Define cómo se toman decisiones, quién las aprueba y qué controles de calidad y
seguridad aplican. Complementa a [SDD](../specs/README.md) y a los
[ADR](../adr/README.md).

## 1. Roles

| Rol | Responsabilidad |
|-----|-----------------|
| **Maintainers** | Aprueban PRs y ADRs, gestionan releases y el backlog. |
| **Security owner** | Revisor obligatorio de cambios sensibles (auth, scraper, infra, secretos). |
| **Contributors** | Proponen specs/ADRs e implementan tareas vía PR. |

Las áreas y revisores obligatorios se definen en
[`.github/CODEOWNERS`](../../.github/CODEOWNERS).

## 2. Toma de decisiones

- **Decisión arquitectónica** → ADR (ver [ADR-0001](../adr/0001-record-architecture-decisions.md)).
- **Comportamiento de producto/feature** → Spec (ver [SDD](../specs/README.md)).
- **Cambio operativo menor** → PR directo con descripción.
- Conflictos no resueltos en revisión: decide el maintainer del área; si afecta a
  seguridad, el *security owner* tiene veto.

## 3. Flujo de ramas y releases

- Rama principal de integración: **`develop`**.
- **Convención de nombres de rama (contrato de prefijos).** Toda rama se nombra
  `<prefijo>/<descripcion-corta>` (kebab-case; opcionalmente `<prefijo>/<n-issue>-…`).
  El prefijo es **obligatorio** y determina la naturaleza del cambio:

  | Prefijo | Uso |
  |---------|-----|
  | `feat/` | Funcionalidades nuevas. |
  | `fix/` | Reparaciones / corrección de bugs. |
  | `docs/` | Documentación (specs, ADR, bitácoras, guías). |
  | `chore/` | Mantenimiento sin impacto funcional (tooling, deps, config). |
  | `sec/` | Cambios de seguridad (auth, hardening, mitigaciones). |

  No se permiten ramas sin prefijo ni con prefijos fuera de esta tabla.
- Todo cambio entra por **PR contra `develop`**; prohibido push directo.
- Releases: se promueve `develop` a la rama/etiqueta de release tras pasar CI y QA.
- Commits convencionales recomendados (`feat:`, `fix:`, `docs:`, `sec:`).

### 3.1 Trabajo dirigido por agentes

El trabajo asistido por agentes ([`.claude/agents/`](../../.claude/agents/)) se rige
por las mismas reglas que el humano, con tres principios propios:

1. **Ejecución por tareas.** Un agente ejecuta el trabajo como **tareas discretas**,
   cada una mapeada a un issue/tarea del backlog. Resuelve **una tarea a la vez**,
   cumpliendo su *Definition of Done* antes de pasar a la siguiente. No se mezclan
   tareas no relacionadas en una misma unidad de entrega.
2. **Trazabilidad por bitácoras.** Cada ejecución que resuelve una tarea deja una
   entrada datada en [`docs/bitacora/`](../../docs/bitacora/) (`tarea-<N>.md`): qué
   se hizo, cumplimiento del DoD, verificación y enlace a la PR. **La bitácora es el
   registro de trazabilidad de oficio** de la actividad de los agentes.
3. **Entrega.** Los agentes que **cambian código** entregan en **rama + PR a
   `develop`** (`Closes #N`), **una PR por unidad revisable**, sin auto-merge ni
   cierre manual del issue. Los agentes que **reconcilian estado externo** (p. ej.
   el backlog del GitHub Project) **no** abren PR de código: operan de forma
   **idempotente, en dry-run por defecto y no destructiva**, y su ejecución queda
   trazada por su informe y por el historial de issues.
4. **Nomenclatura de ramas.** Cada vez que un agente crea una rama, **debe** usar
   el contrato de prefijos de la sección 3 (`feat/`, `fix/`, `docs/`, `chore/`,
   `sec/`), eligiendo el prefijo según la naturaleza del cambio. Nunca crea ramas
   sin prefijo ni trabaja sobre `develop`.

Ningún agente mergea su propia PR, cierra issues a mano ni trabaja sobre `develop`.

## 4. Política de revisión

- Mínimo **1 aprobación** (2 para cambios en áreas de seguridad/infra).
- CI en verde obligatorio (lint, tests, build, escaneo de dependencias).
- Los cambios que tocan áreas de CODEOWNERS requieren a su owner.

## 5. Definition of Ready (DoR) — antes de implementar

Una tarea/épica está *Ready* cuando:
- [ ] Existe spec o issue con problema y **criterios de aceptación verificables**.
- [ ] Riesgos y dependencias identificados.
- [ ] Impacto de seguridad evaluado (¿toca auth, datos, egress, secretos?).
- [ ] Plan de pruebas definido.
- [ ] *(Recomendado, no bloqueante — [ADR-0007](../adr/0007-adopt-spec-kit-authoring-layer.md))*
  La spec pasó el pipeline de autoría Spec Kit: `/speckit-clarify` (ambigüedades
  resueltas) y `/speckit-checklist` del dominio dominante; `/speckit-analyze`
  antes de sembrar el backlog. Ver [speckit-authoring-aids.md](speckit-authoring-aids.md).

## 6. Definition of Done (DoD) — para cerrar

- [ ] Cumple **todos** los criterios de aceptación de la spec.
- [ ] Tests automatizados que cubren el cambio (y pasan en CI).
- [ ] Sin secretos en el diff; dependencias nuevas escaneadas.
- [ ] Documentación/ADR/spec actualizados.
- [ ] Observabilidad: logs/métricas relevantes añadidos si aplica.
- [ ] Revisado y aprobado según la política de revisión.

## 7. Gestión del trabajo

**Fuentes de verdad (separación definición ↔ ejecución):**

| Artefacto | Es fuente de verdad de | Cómo se actualiza |
|-----------|------------------------|-------------------|
| `docs/specs` + `docs/adr` | **Definición**: qué trabajo existe, criterios de aceptación, decisiones | Editando la spec/ADR vía PR (sección 8 *Backlog* de cada spec) |
| **GitHub Project / Issues** | **Ejecución**: open/closed, progreso, asignados, prioridad | En GitHub, durante el trabajo diario |
| `docs/backlog/*.md` | **Overview** humano de alto nivel | A mano, refleja el alcance vigente |

- El backlog operativo vive en el **GitHub Project**; épicas y tareas etiquetadas
  por `epic`/`task`, `area/*` y `sev/*`.
- La **definición** de épicas/tareas se declara en el bloque estructurado
  `sdd-sync` de cada spec (sección 8 del [TEMPLATE](../specs/TEMPLATE.md)). El
  agente [`sdd-sync`](../../.claude/agents/sdd-sync.md) (comando `/sdd-sync`)
  reconcilia esa definición con los issues: **crea/actualiza** la definición pero
  **nunca** toca el estado de ejecución (no cierra/reabre/borra). Dry-run por
  defecto; aplica con `--apply`.
- Las specs **nacen y maduran** con la capa de autoría Spec Kit
  (`/speckit-specify` → `/speckit-clarify` → `/speckit-checklist` →
  `/speckit-analyze`), recomendada en la DoR (§5) y documentada en
  [speckit-authoring-aids.md](speckit-authoring-aids.md) (ADR-0007). **Toda
  épica del Project debe estar respaldada por una spec** con bloque `sdd-sync`
  (las tareas del bootstrap sin spec se adoptaron en SPEC-015…020).
- [`scripts/seed_github_project.py`](../../scripts/seed_github_project.py) es un
  **bootstrap de un solo uso** (creación inicial del Project), **no** un sync
  incremental. Para mantener el backlog al día tras el bootstrap se usa `/sdd-sync`.
- Prioridad: primero 🔴, luego 🟠 de bajo esfuerzo, según
  [ADR-0003](../adr/0003-security-baseline-and-threat-model.md).
- **Áreas registradas** (`area/*`): `security`, `infra`, `backend`,
  `observability`, `governance`, `ux`, `evaluation`. Dar de alta un área nueva es
  un cambio de gobernanza: añadirla a `ALLOWED_AREAS`
  ([`validate_specs.py`](../../scripts/validate_specs.py)) y a `LABELS`
  ([`seed_github_project.py`](../../scripts/seed_github_project.py)), crear la label
  en GitHub y reflejarla aquí y en el backlog.

### 7.1 Evaluation-Driven Development (EDD)

Complementa al SDD para los componentes **probabilísticos** (agentes/modelos). El
*qué* se gobierna por SDD; el *cómo de bien se comporta* lo gobierna EDD
([ADR-0006](../adr/0006-adopt-evaluation-driven-development.md), área
`area/evaluation`, épica E9):

- El comportamiento de los agentes se respalda con **evals versionadas**
  (`backend/evals/`): datasets *golden* + métricas de comportamiento. **Alcance
  limitado a los agentes/modelos de la plataforma**, no a modelos *foundation*
  globales.
- Un cambio en `prompt_template`, `model` o `temperature` de un agente debe pasar
  el **gate EDD** (regresión sobre umbrales declarados); arranca como aviso y se
  endurece tras fijar la línea base.
- La **explicabilidad** ([SPEC-014](../specs/SPEC-014-explainability-and-edd.md)) es
  el sustrato de datos de las evals: traza auditable por paso de cada ejecución.

## 8. Datos y cumplimiento

- PII tratada (emails, contenidos) sujeta a la política de retención
  (épica E6). No registrar secretos ni PII en logs.
- Reporte de vulnerabilidades: ver [`SECURITY.md`](../../SECURITY.md).
