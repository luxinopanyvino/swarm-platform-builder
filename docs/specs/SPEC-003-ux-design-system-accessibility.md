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

- [x] **AC1** — *Given* el código de `frontend/src`, *When* se busca color
  hexadecimal literal en JSX/CSS, *Then* no hay coincidencias: todo color usa
  un token (`var(--…)`) o la escala del design system.
  <br>*T7.1 (#192)*: 82 hexes sustituidos en 11 ficheros. Única exención,
  `src/paperTheme.js`: son los colores del **paper impreso**, espejo de
  `_THEME_ACCENTS` del backend — la muestra debe enseñar el color del PDF, no el
  de la aplicación; hay un test que comprueba que el espejo sigue siendo fiel.
- [x] **AC2** — *Given* un usuario que navega solo con teclado, *When* abre un
  modal (p. ej. editor de agentes), *Then* el foco queda atrapado en el modal,
  es **visible**, y `Esc` lo cierra devolviendo el foco al disparador.
  <br>*T7.2 (#193)*: el contrato lo implementa un único componente,
  `src/components/ui/Modal.jsx`, y los seis diálogos de la aplicación pasan por
  él. Foco visible mediante `:focus-visible` global con `outline-offset` (antes no
  había ninguno, y cuatro campos lo apagaban con `outline: none` en línea).
  Verificado **con teclas reales en Chromium** sobre el componente construido, no
  leyendo el código.
- [x] **AC3** — *Given* los pares texto/fondo de los componentes base
  (botones, badges, inputs), *When* se mide el contraste, *Then* cumplen
  **WCAG 2.1 AA** (≥ 4.5:1 texto normal; ≥ 3:1 texto grande/iconos).
  <br>*T7.2 (#193)*: `scripts/check_contrast.py` mide 30 pares en tema claro y
  oscuro. Partían 18 por debajo del umbral; se corrigieron **en los tokens**, no
  en los componentes. Los separadores decorativos se miden pero no bloquean: no
  son contorno de ningún control y WCAG no les fija umbral.
- [x] **AC4** — *Given* una página con datos remotos (artículos, agentes,
  documentos), *When* está cargando / sin datos / con error, *Then* muestra un
  estado **loading / empty / error** consistente y reutilizable.
  <br>*T7.3 (#194)*: `src/components/ui/states.jsx` — `LoadingState`,
  `EmptyState`, `ErrorState` y el compositor `AsyncState`, adoptados por las
  once vistas con datos remotos. El estado de **error no existía**: toda carga
  fallida acababa en un `toast` que se va solo y dejaba en pantalla el estado
  **vacío**, diciendo que no había datos cuando lo que pasaba es que no se habían
  podido pedir. Los stores ahora guardan el error y el estado ofrece reintentar.
- [x] **AC5** — Existe una comprobación automatizable (lint/script) que valida
  AC1 y un checklist verificable para AC2–AC4.
  <br>*T7.1 (#192)*: hecha la mitad automatizable —
  `scripts/check_design_tokens.py`, en el job `frontend-build` de la CI. Además
  del hex literal detecta `var(--token)` **que no existe**, que es el fallo
  silencioso: sin fallback la propiedad se descarta y el elemento no pinta nada
  (había 6 en `main`, ya corregidos).
  <br>*T7.2 (#193)*: AC2 y AC3 no se quedan en checklist — son comprobaciones
  automatizadas. AC3 lo mide `scripts/check_contrast.py` en la CI; AC2 lo
  comprueba `backend/tests/test_modal_a11y.py`, con una capa estructural que
  siempre corre y una capa de teclado en Chromium que se salta si no hay
  navegador (hoy, en la CI, se salta).
  <br>*T7.3 (#194)*: cierra AC5. AC4 tampoco se queda en checklist:
  `scripts/check_async_states.py` corre en la CI y comprueba que nadie pinte un
  estado a mano ni se trague un error de carga sin motivo escrito. Los cuatro
  criterios quedan con comprobación automatizada y no con lista de repaso:
  **AC1** `check_design_tokens.py`, **AC3** `check_contrast.py`, **AC4**
  `check_async_states.py` y **AC2** los tests de teclado.

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
