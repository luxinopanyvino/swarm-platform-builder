# Release Notes

---

## v1.0.0 — Primera versión del Design System Alexandria

**Fecha:** Junio 2025  
**Tipo:** Release inicial

Esta es la primera versión del Design System de Alexandria Magazine. Establece la fuente única de verdad visual para el producto — reemplazando el CSS ad-hoc disperso por un sistema de tokens coherente, escalable, y con soporte de dark mode.

---

### Cambios principales

#### Migración de dark purple/cyan a SLDS2 Blue

El producto original usaba un tema oscuro con violeta `#7c3aed` como brand y cyan `#06b6d4` como accent. Esta versión **pivota a una dirección editorial clara (light-first)** basada en Salesforce Lightning Design System 2.

| Antes | Ahora |
|---|---|
| Brand: `#7c3aed` (purple) | Brand: `#0176D3` (Alexandria Blue, SLDS2) |
| Accent: `#06b6d4` (cyan) | Accent: `#6B4FE3` (violet, IA-only) |
| Tema por defecto: dark | Tema por defecto: light |
| Sin sistema de tokens | Sistema completo de tokens CSS (3 capas) |

El violeta se retiene como **accent restringido para momentos IA** — continuidad con la identidad original sin hacerlo dominante.

---

#### Sistema de tokens CSS en tres capas

Nuevo archivo `colors_and_type.css` como fuente única de verdad:

- **Primitivos:** ramps de color completos (`--blue-*`, `--neutral-*`, `--ink-*`, `--violet-*`)
- **Escalas:** tipo, espaciado, radius, motion — compartidas entre temas
- **Semánticos:** `--brand`, `--bg-surface`, `--text-heading`, etc. — la capa de construcción

Dark theme completo via `[data-theme="dark"]` — solo los semánticos se redefinen.

---

#### Tres tipografías de sistema

Nuevo stack tipográfico de código abierto (OFL), cargado desde Google Fonts:

| Tipografía | Uso | Antes |
|---|---|---|
| **Source Serif 4** | Contenido editorial (.prose) | Sin tipografía editorial |
| **Source Sans 3** | UI del producto (.ax) | System font stack |
| **JetBrains Mono** | Código y metadatos | Menlo / monospace genérico |

Dos registros tipográficos con clases CSS: `.ax` (Studio UI) y `.prose` (Magazine editorial).

---

#### Paleta de agentes

Cinco colores con identidad propia para los agentes del pipeline editorial:

| Agente | Color | Token |
|---|---|---|
| Investigador | `#0D9DDA` | `--agent-research` |
| Redactor | `#6B4FE3` | `--agent-write` |
| Revisor | `#C47D04` | `--agent-review` |
| Formateador | `#2E844A` | `--agent-format` |
| Publicador | `#CB4B3F` | `--agent-publish` |

Los emojis de agente (🔍✍️👁️📄🚀) se reemplazan por iconos Lucide.

---

#### Dark theme

Dark theme completo con valores independientemente ajustados para mantener contraste AA en superficies oscuras. El brand sube a `#2F9BFF` para AA sobre `#0A1120`.

---

#### Tokens W3C DTCG

Exportación de todos los tokens en formato W3C Design Token Community Group (`tokens.dtcg.json`) para importar en Figma Variables, Style Dictionary, y Tokens Studio.

---

#### Documentación completa

- `README.md` — contexto del producto, visual foundations, iconografía
- `tokens.md` — arquitectura de tokens y patrones de diseño
- `ACCESSIBILITY.md` — WCAG 2.1 AA vinculante
- `preview/` — 30+ specimens HTML de componentes y fundamentos
- `zeroheight/` — paquete de contenido para el styleguide Zeroheight

---

### Migración desde el CSS legacy

Si tu componente usaba las variables antiguas del `index.css` original:

| Variable anterior | Variable nueva |
|---|---|
| `--primary: #7c3aed` | `--brand: var(--blue-60)` |
| `--primary-hover: #6d28d9` | `--brand-hover: var(--blue-70)` |
| `--accent-cyan: #06b6d4` | Eliminado — no tiene equivalente directo |
| `--bg-dark: #0f172a` | `--bg-canvas` (dark theme) |
| `--text-primary: #f8fafc` | `--text-heading` / `--text-body` |
| Sin tokens de agente | `--agent-research/write/review/format/publish` |

---

### Próximos pasos (backlog)

- [ ] Biblioteca de componentes React documentada (Storybook o equivalente)
- [ ] Figma library sincronizada con Variables vía Tokens Studio
- [ ] UI kit de Magazine (lector de artículos) en Figma
- [ ] Tokens de dataviz en Figma
- [ ] Motion library (Framer Motion) alineada con `--dur-*` y `--ease-*`
