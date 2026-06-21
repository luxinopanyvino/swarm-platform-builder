# Getting Started

Cómo empezar a trabajar con el Design System de Alexandria Magazine, tanto si eres diseñador como desarrollador.

---

## Para diseñadores

El sistema de diseño está basado en **tokens CSS** (`colors_and_type.css`) que se sincronizan con variables de Figma. El archivo fuente contiene todos los valores de color, tipografía, espaciado, radius, sombras y motion.

### Paso 1 — Instalar las fuentes

Las tres tipografías son open-source y se cargan desde Google Fonts. En Figma, instala las fuentes desde el gestor de fuentes de tu sistema operativo o usa el plugin de Google Fonts:

- **Source Serif 4** — pesos 400, 500, 600, 700
- **Source Sans 3** — pesos 400, 500, 600, 700 (regular e itálica)
- **JetBrains Mono** — pesos 400, 500, 600

### Paso 2 — Importar los tokens como variables de Figma

Los tokens están en formato W3C DTCG (`tokens.dtcg.json`). Usa el plugin **Tokens Studio** o **Variables Import** de Figma para importarlos como variables de color y tipografía.

Una vez importados:
- Los colores primitivos (`blue-60`, `neutral-10`, etc.) aparecen en la librería de variables
- Los semánticos (`brand`, `bg-surface`, `text-heading`) se crean como alias que apuntan a los primitivos
- El tema oscuro se activa cambiando la colección de variables a `dark`

### Paso 3 — Dos superficies, dos modos

Diseña siempre sabiendo en qué superficie trabajas:

- **Studio** — interfaz de autoría: sans, compacta, funcional
- **Magazine** — lectura editorial: serif, generosa, académica

No mezcles tipografías de registro entre superficies.

### Iconografía

Usa el plugin de **Lucide** en Figma, o importa los iconos SVG. Stroke de 1.5px, `currentColor`, sin fill. Tamaños: 14–18px en UI inline, 24–28px en empty states.

---

## Para desarrolladores

### Instalación

El design system no es un paquete npm — es un archivo CSS que se importa directamente. El stack del proyecto es **React 18 + Vite**.

**Paso 1 — Importar los tokens**

```css
/* En tu CSS global o index.css */
@import '../ds/colors_and_type.css';
```

O con una ruta absoluta según la estructura del proyecto:

```css
@import '/frontend/ds/colors_and_type.css';
```

**Paso 2 — Aplicar el registro tipográfico**

```html
<!-- Studio / app UI -->
<body class="ax">
  <!-- Aquí aplica Source Sans 3, 14px, bg-canvas -->
</body>

<!-- O para una sección específica -->
<div class="ax-root">
  <!-- Componentes del Studio -->
</div>
```

```html
<!-- Artículo publicado -->
<article class="prose">
  <!-- Aquí aplica Source Serif 4, 16px, measure 68ch -->
  <h1>Título del artículo</h1>
  <p>Texto del artículo...</p>
</article>
```

**Paso 3 — Usar variables semánticas**

Siempre variables semánticas, nunca primitivas ni hex hardcodeados:

```css
/* ✅ Correcto */
.mi-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-1);
  padding: var(--space-lg);
}

/* ❌ Incorrecto */
.mi-card {
  background: #ffffff;
  border: 1px solid #E0E5EE;
  border-radius: 12px;
  padding: 24px;
}
```

**Paso 4 — Iconos con Lucide**

```bash
# Ya instalado en el proyecto — verificar package.json
npm install lucide-react
```

```jsx
import { Search, BookOpen, Bot, Zap, CheckCircle } from 'lucide-react';

// En el componente
<Search size={16} />           // UI inline
<BookOpen size={24} />         // Empty state icon tile
```

**Paso 5 — Tema oscuro**

```jsx
// Aplicar en cualquier ancestro
<html data-theme="dark">

// O en una sección específica
<section data-theme="dark">
  {/* Todos los componentes dentro heredan el tema */}
</section>

// O con clase
<div className="dark">
```

---

## Estructura de archivos del DS

```
frontend/ds/
├── README.md              ← Contexto completo, visual foundations
├── colors_and_type.css    ← FUENTE DE VERDAD — todos los tokens CSS
├── tokens.md              ← Arquitectura de tokens y patrones
├── ACCESSIBILITY.md       ← Normas WCAG 2.1 AA vinculantes
├── SKILL.md               ← Entry point para el agente de diseño
├── assets/
│   ├── logomark.svg       ← Monograma "A" en tile azul
│   └── wordmark.svg       ← Mark + "Alexandria" + "MAGAZINE"
└── preview/               ← 30+ specimens HTML de componentes
```

---

## Flow Designer

El Flow Designer usa **`@xyflow/react`** para el canvas de agentes. Los nodos de agente heredan el sistema de color por agente (`--agent-research`, `--agent-write`, etc.) y el sistema de tokens estándar. Los bordes de flujo animan (marching ants) y deben pausarse con `prefers-reduced-motion`.

---

## Checklist antes de hacer PR

- [ ] Usando variables semánticas CSS (`--brand`, `--bg-surface`, etc.) — no hex ni primitivas
- [ ] Tipografía en el registro correcto (`.ax` para UI, `.prose` para contenido)
- [ ] Iconos Lucide, no emoji
- [ ] Focus ring visible en todos los controles interactivos
- [ ] Contraste AA verificado en pares de color nuevos
- [ ] Tema oscuro comprobado con `data-theme="dark"`
- [ ] Labels en todos los inputs, errores en texto + icono
