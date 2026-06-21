# Design

Cómo usar el Design System de Alexandria Magazine como diseñador — fundamentos, estructura, y las dos superficies del producto.

---

## Base del sistema

Alexandria Magazine Design System está construido sobre **Salesforce Lightning Design System 2 (SLDS2)** — la estructura de tokens (primitivo → alias → semántico), la escala de espaciado rem, y la familia de colores cloud — reenmarcado para una estética editorial y científica.

Lo que el sistema añade que SLDS no tiene:
- **Tipografía editorial:** Source Serif 4 para largo lectura + Source Sans 3 para UI
- **Paleta de agentes:** 5 colores con identidad propia para los agentes del pipeline
- **Content System:** `.prose` con measure, leading, y ritmo académico para artículos publicados
- **Estados editoriales:** ciclo de vida del artículo como sistema de tokens de color
- **Accent IA:** violeta para momentos de inteligencia artificial

---

## Las dos superficies

Siempre diseña sabiendo en qué superficie trabajas:

### Studio — espacio de trabajo del investigador

**Vibe:** productivity app moderna, back office de una publicación científica. Blanca, espaciosa, funcional.

- Superficies: canvas `#F4F6F9` → cards blancas → sidebar blanco
- Tipografía: Source Sans 3, 14px body, compacta
- Color de acción: Alexandria Blue `#0176D3`
- Iconos: Lucide, 1.5px stroke, 14–18px inline
- Layouts: sidebar 248px fijo + topbar 56px + content area scrollable
- Cards: blancas, radius 12px, shadow-1 → shadow-2 hover

**Páginas principales:** Auth, Flow Designer canvas, lista de artículos, editor de artículo, panel de revisión, configuración

### Magazine — capa de lectura pública

**Vibe:** publicación científica moderna. Serif, generosa, académica.

- Columna centrada a `68ch`
- Tipografía: Source Serif 4, 16px body, 1.7 leading
- Sin sidebar en la vista de artículo
- Artículos con abstract, secciones, figuras, callouts, referencias
- Cover imagery: foto cool y limpia detrás de ink scrim

---

## Sistema de tokens → variables Figma

Los tokens CSS de `colors_and_type.css` se sincronizan en Figma como variables de color:

**Colección: Primitives**
- `blue/60` = #0176D3
- `neutral/10` = #F4F6F9
- `ink/100` = #0B1B33
- ... (todos los primitivos)

**Colección: Semantic / Light** (alias que apuntan a Primitives)
- `brand/default` → `blue/60`
- `background/surface` → `neutral/00`
- `text/heading` → `ink/100`

**Colección: Semantic / Dark** (overrides del dark theme)
- `brand/default` → `#2F9BFF`
- `background/surface` → `#111C2F`
- `text/heading` → `#F3F6FC`

Al cambiar la colección activa en Figma de Light a Dark, todos los componentes que usan variables semánticas cambian automáticamente.

---

## Iconografía en Figma

Usar el plugin de Lucide en Figma. Stroke de 1.5px, rounded caps y joins, sin fill. Color: `currentColor` (heredar del texto del contexto).

**Tamaños:**
- 14–18px: UI inline (botones, nav, labels)
- 11–13px: dentro de badges
- 24–28px: empty states en icon tile
- 20px: avatares placeholder

**Icon tiles** (fondo tintado + icono del color del agente/marca):
- Background: tint 05 del color del agente
- Icono: color full del agente
- Radius: `--radius-lg` (12px) o `--radius-circle` (50%)

---

## Logo

- `assets/logomark.svg` — monograma "A" pedimento griego en tile azul. Mínimo 24px. ½ tile de clear space en todos lados.
- `assets/wordmark.svg` — mark + "Alexandria" en serif + "MAGAZINE" eyebrow.

En fondos oscuros o fotográficos: usar variante white-on-blue tile.

---

## Grids y layouts

**Studio:**
- Desktop: 12 columnas, 24px gutter, margins 24px+
- Sidebar fijo 248px, topbar 56px
- Content area: fluida, padding 32px top / 48px lados

**Magazine:**
- Single column centrada a `68ch`
- Padding top: `64px` (space-3xl)
- Sin columnas laterales en la vista de artículo

---

## Checklist del diseñador antes de entregar specs

- [ ] Variables semánticas usadas (no colores primitivos ni hex custom)
- [ ] Source Sans 3 para UI, Source Serif 4 para contenido
- [ ] Iconos Lucide especificados con tamaño y color
- [ ] Estados (hover, active, focus, disabled) especificados en cada componente
- [ ] Focus ring visible en prototipo
- [ ] Dark theme verificado si aplica
- [ ] Empty states diseñados para todas las listas y canvas
- [ ] Error states diseñados para todos los formularios
- [ ] Contraste verificado en combinaciones custom
