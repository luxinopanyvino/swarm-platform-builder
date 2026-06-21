# Testing Accessibility

Antes de cada release, cada pantalla y flujo nuevo pasa por un checklist mínimo de accesibilidad. Las herramientas aquí documentadas cubren los errores más comunes y los más difíciles de detectar visualmente.

---

## Herramientas recomendadas

### Automatizadas

**axe DevTools** (extensión Chrome/Firefox)
La herramienta de auditoría automatizada más completa. Detecta ~57% de los problemas WCAG sin manual. Instalar la extensión gratuita o usar `@axe-core/react` en desarrollo.

```bash
npm install --save-dev @axe-core/react

# En desarrollo (dev mode only)
if (process.env.NODE_ENV !== 'production') {
  const axe = require('@axe-core/react');
  axe(React, ReactDOM, 1000);
}
```

**Lighthouse** (Chrome DevTools → Lighthouse → Accessibility)
Auditoría integrada en Chrome. Corre en cada página en CI/CD para detectar regresiones.

**Wave** (extensión Chrome/Firefox)
Visualización de estructura de headings, landmarks, y errores ARIA. Útil para revisión rápida de semántica.

---

### Screen readers

**VoiceOver (macOS / iOS)** — `Cmd + F5` para activar
Probar con Safari en macOS. Flujo básico:
1. Navegar con Tab por todos los controles interactivos
2. Verificar que cada botón e input anuncia correctamente su nombre y estado
3. Verificar que los toasts y alertas se anuncian sin mover el foco
4. Verificar que los modales atrapan el foco y anuncian su título

**NVDA (Windows)** — Gratis, con Firefox
El screen reader más usado en Windows. Complementar VoiceOver para cobertura cruzada.

---

### Contraste de color

**Colour Contrast Analyser** (app desktop, Paciello Group)
Para verificar pares de color custom o combinaciones sobre imágenes. Eyedropper para colores de pantalla.

**Who Can Use** (whocanyuse.com)
Simula cómo distintos tipos de visión perciben combinaciones de color. Útil para verificar paletas.

---

## Checklist mínimo por pantalla

### Contraste y color
- [ ] Texto y UI no-texto pasan el ratio mínimo de su nivel (4.5:1 / 3:1)
- [ ] Ningún estado se comunica solo con color — siempre + texto + icono
- [ ] Charts y visualizaciones tienen etiquetas directas o leyenda

### Teclado
- [ ] Tab alcanza todos los controles interactivos
- [ ] El orden de tab es lógico y sigue el flujo visual
- [ ] Enter activa botones, Space activa checkboxes/radios
- [ ] Esc cierra modales, dropdowns, tooltips
- [ ] Focus ring visible en cada estado `:focus-visible`

### Screen reader (VoiceOver mínimo)
- [ ] Nombre anunciado correcto en botones (incluyendo icon-only)
- [ ] Inputs anuncian su label y estado (`aria-invalid`)
- [ ] Errores se anuncian cuando aparecen (`role="alert"`)
- [ ] Toasts de éxito se anuncian sin interrumpir (`aria-live="polite"`)
- [ ] Modales anuncian su título y atrapan el foco

### Estructura
- [ ] Un solo `<h1>` por vista
- [ ] Jerarquía de headings correcta (no saltar niveles)
- [ ] Landmarks presentes: `<nav>`, `<main>`, `<header>`
- [ ] Imágenes no decorativas tienen `alt` descriptivo

### Formularios
- [ ] Cada `<input>` tiene `<label>` visible persistente
- [ ] Errores asociados con `aria-describedby`
- [ ] Campos requeridos marcados (`required` / `aria-required`)

### Motion
- [ ] Animaciones pausadas bajo `prefers-reduced-motion: reduce`
- [ ] Spinners de agente pausan correctamente
- [ ] Flow Designer edges pausan animación en motion reducida

---

## Flujos críticos a probar con teclado

1. **Login** — email → password → botón "Iniciar sesión"
2. **Crear artículo** — botón crear → modal → título → guardar
3. **Flow Designer** — abrir panel → agregar agente (alternativa a drag) → ejecutar
4. **Aprobar artículo** — abrir artículo → acción aprobar → confirmación
5. **Eliminar artículo** — modal de confirmación → botón "Eliminar artículo"

---

## Herramientas en CI

Para prevenir regresiones, integrar axe en los tests de Playwright/Cypress:

```js
// Playwright + axe-playwright
import { checkA11y } from 'axe-playwright';

test('Articles list is accessible', async ({ page }) => {
  await page.goto('/articles');
  await checkA11y(page, null, {
    detailedReport: true,
    detailedReportOptions: { html: true },
  });
});
```

---

## Regresión de accesibilidad

Si axe reporta un error que antes no existía, es una regresión de accesibilidad y bloquea el merge. Tratar con la misma prioridad que un bug visual de producción.
