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
- Convención de ramas: `feat/…`, `fix/…`, `docs/…`, `chore/…`, `sec/…`.
- Todo cambio entra por **PR contra `develop`**; prohibido push directo.
- Releases: se promueve `develop` a la rama/etiqueta de release tras pasar CI y QA.
- Commits convencionales recomendados (`feat:`, `fix:`, `docs:`, `sec:`).

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

## 6. Definition of Done (DoD) — para cerrar

- [ ] Cumple **todos** los criterios de aceptación de la spec.
- [ ] Tests automatizados que cubren el cambio (y pasan en CI).
- [ ] Sin secretos en el diff; dependencias nuevas escaneadas.
- [ ] Documentación/ADR/spec actualizados.
- [ ] Observabilidad: logs/métricas relevantes añadidos si aplica.
- [ ] Revisado y aprobado según la política de revisión.

## 7. Gestión del trabajo

- El backlog vive en el **GitHub Project** del repositorio (ver
  `docs/backlog/`). Épicas y tareas etiquetadas por `area/*` y `sev/*`.
- Prioridad: primero 🔴, luego 🟠 de bajo esfuerzo, según
  [ADR-0003](../adr/0003-security-baseline-and-threat-model.md).

## 8. Datos y cumplimiento

- PII tratada (emails, contenidos) sujeta a la política de retención
  (épica E6). No registrar secretos ni PII en logs.
- Reporte de vulnerabilidades: ver [`SECURITY.md`](../../SECURITY.md).
