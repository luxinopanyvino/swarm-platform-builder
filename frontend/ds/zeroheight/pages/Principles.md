# Design Principles

Los principios de Alexandria Magazine no son aspiracionales — son restricciones activas. Cada decisión de diseño, cada componente y cada patrón responde a alguno de estos cinco principios.

---

## 1. Precisión y calma

Alexandria es una herramienta para científicos. El trabajo que se hace aquí es riguroso, lento, y de alto coste cognitivo. La interfaz no debe añadir fricción ni ruido visual.

**En la práctica:**
- Superficies blancas o gris-azulado muy tenue. Sin gradientes ni texturas decorativas.
- Un solo color de acción (Alexandria Blue) por vista. El resto de color es funcional.
- Sin signos de exclamación en copy de producto. "Flujo guardado", no "¡Tu flujo se guardó con éxito! 🎉".
- Sin emoji en UI. Sin animaciones llamativas. Motion utilitario: 120–320ms, ease estándar.
- Sombras suaves, ink-tinted. Sin neón glows.

---

## 2. Jerarquía editorial

El contenido tiene estructura. Los artículos científicos tienen título, abstract, secciones, figuras, referencias. La interfaz debe reflejar esa estructura sin aplanarla.

**En la práctica:**
- Dos registros tipográficos distintos y deliberados: sans para el chrome, serif para el contenido.
- Heading hierarchy respetada — h1 → h2 → h3 sin saltar niveles.
- Los estados del artículo (borrador, en revisión, aprobado, publicado) son visibles y exactos — siempre etiqueta + color + icono.
- Las cards de artículo llevan el título como protagonista (Source Serif 4), no los metadatos.

---

## 3. Contenido primero

Alexandria existe para producir artículos, no para exhibir la interfaz. El chrome — sidebar, topbar, controles — debe ser invisible cuando el usuario está en modo de lectura o escritura.

**En la práctica:**
- La columna de lectura `.prose` es `68ch` centrada, sin elementos que compitan.
- El canvas del Studio es gris tenue, no blanco puro — para que las cards y paneles blancos resalten sobre él, no al revés.
- El sidebar tiene 248px: suficiente para navegar, no tanto como para dominar.
- Las acciones IA (`btn-accent`, violeta) se distinguen visualmente del flow principal — no compiten con el primario.

---

## 4. Accesibilidad por defecto

WCAG 2.1 AA no es un post-proceso — está integrado en los tokens. Los pares de color semántico están pre-verificados. El focus ring siempre es visible. Las reglas son vinculantes para todo lo que se construya con este sistema.

**En la práctica:**
- Contraste mínimo 4.5:1 para texto normal, 3:1 para UI.
- Estado nunca comunicado solo con color — siempre + etiqueta + icono Lucide.
- Focus ring 3px azul visible en todos los controles interactivos.
- Targets mínimos 44×44px para acciones primarias.
- `prefers-reduced-motion` respetado — pausar animaciones decorativas.
- `lang="es"` en el root; cambiar `lang` en contenido en otro idioma.

---

## 5. Dos registros

Studio y Magazine son dos superficies del mismo producto, pero con modos cognitivos distintos. La herramienta de autoría vs. la publicación terminada. Esta distinción es deliberada y debe mantenerse.

**En la práctica:**

| Dimensión | Studio UI (`.ax`) | Magazine (`.prose`) |
|---|---|---|
| Tipografía | Source Sans 3, 14px | Source Serif 4, 16px |
| Line-height | 1.5 (normal) | 1.7 (relaxed) |
| Densidad | Compacto, funcional | Generoso, académico |
| Measure | Sin límite fijo | 68ch centrado |
| Tono de color | SLDS cloud, blue | Ink-navy, serif |
| Propósito | Trabajar | Leer |

Mezclar los registros — usar serif en UI o sans en contenido long-form — es un error de diseño, no una variación válida.
