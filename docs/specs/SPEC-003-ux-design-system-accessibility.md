# SPEC-003: Sistema de diseño y accesibilidad de la UI

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-06-28
- **Épica:** E7 (UX/UI)
- **ADR relacionado:** —
- **Severidad:** 🟠

## 1. Problema

La UI del frontend mezcla **colores hardcodeados** (`#ef4444`, `#6366f1`,
`#10b981`…) repartidos por componentes y páginas, en lugar de usar los **tokens
de diseño** ya definidos en [`frontend/ds/zeroheight/tokens.dtcg.json`](../../frontend/ds/zeroheight/tokens.dtcg.json)
y las variables CSS (`var(--brand)`, `var(--error)`…). Esto produce:

- inconsistencia visual y *drift* respecto al design system,
- dificultad para temas (claro/oscuro) y para cambios globales de marca,
- accesibilidad sin garantizar: contraste, foco visible y navegación por teclado
  no están verificados (p. ej. en modales como el editor de agentes).

No hay criterios objetivos de "UI correcta" ni una comprobación que lo valide.

## 2. Objetivos / No-objetivos

- **Objetivos:**
  - Unificar el color y el espaciado en **tokens** (cero hex hardcodeado en `src`).
  - Garantizar **accesibilidad AA** en componentes interactivos clave.
  - Estados de **carga / vacío / error** consistentes en las páginas principales.
- **No-objetivos:** rediseño visual completo, migrar de framework de estilos, ni
  internacionalización (futuras specs).

## 3. Criterios de aceptación (Given/When/Then)

- [ ] **AC1** — *Given* el código de `frontend/src`, *When* se busca color
  hexadecimal literal en JSX/CSS, *Then* no hay coincidencias: todo color usa
  un token (`var(--…)`) o la escala del design system.
- [ ] **AC2** — *Given* un usuario que navega solo con teclado, *When* abre un
  modal (p. ej. editor de agentes), *Then* el foco queda atrapado en el modal,
  es **visible**, y `Esc` lo cierra devolviendo el foco al disparador.
- [ ] **AC3** — *Given* los pares texto/fondo de los componentes base
  (botones, badges, inputs), *When* se mide el contraste, *Then* cumplen
  **WCAG 2.1 AA** (≥ 4.5:1 texto normal; ≥ 3:1 texto grande/iconos).
- [ ] **AC4** — *Given* una página con datos remotos (artículos, agentes,
  documentos), *When* está cargando / sin datos / con error, *Then* muestra un
  estado **loading / empty / error** consistente y reutilizable.
- [ ] **AC5** — Existe una comprobación automatizable (lint/script) que valida
  AC1 y un checklist verificable para AC2–AC4.

## 4. Diseño propuesto

- Centralizar tokens en CSS variables derivadas de `tokens.dtcg.json`; sustituir
  los hex literales por `var(--…)` en componentes y páginas.
- Componente(s) reutilizables de estado: `<LoadingState/>`, `<EmptyState/>`,
  `<ErrorState/>`.
- Utilidad de *focus trap* + estilos de foco visibles para modales/diálogos.
- Script de lint (p. ej. regex o regla ESLint) que falle ante hex hardcodeado.

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Regresiones visuales al migrar colores | Medio | Migración por páginas + revisión visual |
| Falsos positivos del lint de color (assets, datos) | Bajo | Allowlist de rutas/archivos |
| Focus trap rompe componentes existentes | Bajo | Aplicar solo a modales y probar por teclado |

## 6. Plan de pruebas

- Lint/script de color sobre `frontend/src` (AC1, AC5).
- Pruebas manuales de teclado en los modales principales (AC2).
- Medición de contraste de los componentes base con herramienta a11y (AC3).
- Revisión de los estados loading/empty/error en las páginas clave (AC4).

## 7. Impacto operativo / observabilidad

- Documentar los tokens y los componentes de estado en la guía de frontend.
- El lint de color se integra en la CI (job de frontend) cuando esté disponible.

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E7
  title: "Experiencia de Usuario (UX/UI)"
  area: area/ux
tasks:
  - id: T7.1
    title: Unificar colores en tokens de diseño (sin hex hardcodeado)
    sev: medium
    depends_on: []
    acceptance: [AC1, AC5]
  - id: T7.2
    title: Accesibilidad AA en modales (focus trap, foco visible, Esc)
    sev: medium
    depends_on: []
    acceptance: [AC2, AC3]
  - id: T7.3
    title: Estados consistentes de carga / vacío / error
    sev: low
    depends_on: [T7.1]
    acceptance: [AC4]
```
