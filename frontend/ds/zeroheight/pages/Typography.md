# Typography

Alexandria Magazine emplea tres tipografías de código abierto (licencia OFL), cargadas desde Google Fonts. El sistema tipográfico responde a dos registros distintos: **Studio UI** — compacto, sans, funcional — y **Magazine** — editorial, serif, generoso en espacio.

```css
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600;8..60,700&family=Source+Sans+3:ital,wght@0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap');
```

---

## Las tres tipografías

### Source Serif 4 — contenido editorial

La voz editorial de Alexandria. Tipografía de texto óptico de Adobe, diseñada para larga lectura a cuerpos confortables. Se usa en:
- Artículos publicados (`.prose`)
- Display headings del Magazine
- Pull quotes y extractos destacados
- Títulos de artículos en cards de lista

**Token:** `--font-serif: 'Source Serif 4', Georgia, 'Times New Roman', serif`

Pesos disponibles: 400 (regular), 500 (medium), 600 (semibold), 700 (bold)
Eje óptico: `8..60` — ajusta automáticamente para display y texto

---

### Source Sans 3 — UI del producto

La voz funcional del Studio. La misma familia que Source Serif, en registro sans — coherencia tipográfica entre Chrome y contenido. Se usa en:
- Navegación, botones, labels, controles
- Metadatos, captions, tablas de datos
- Mensajes de estado, toasts, alertas
- Toda la interfaz de usuario del Studio

**Token:** `--font-sans: 'Source Sans 3', system-ui, -apple-system, 'Segoe UI', sans-serif`

Pesos disponibles: 400, 500, 600, 700 (regular e itálica)

---

### JetBrains Mono — código y datos

Monoespaciada diseñada para programadores por JetBrains. Ligaduras de código, alta legibilidad en pantalla. Se usa en:
- Bloques de código en artículos
- Payloads JSON / RAG output
- Nombres de tokens en este documento
- Metadatos de formato (APA/IEEE/Vancouver)
- Etiquetas técnicas y valores de configuración

**Token:** `--font-mono: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace`

Pesos disponibles: 400, 500, 600

---

## Escala tipográfica

| Token CSS | rem | px | Uso |
|---|---|---|---|
| `--text-2xs` | 0.6875rem | 11px | Labels de badge, eyebrows de tabla (CAPS) |
| `--text-xs` | 0.75rem | 12px | Captions, overlines, metadatos pequeños |
| `--text-sm` | 0.8125rem | 13px | Labels secundarios, body de tooltip |
| `--text-base` | 0.875rem | **14px** | **Body UI por defecto** (Studio) |
| `--text-md` | 1rem | **16px** | **Body lectura mínimo** (Magazine) |
| `--text-lg` | 1.125rem | 18px | Subheadings UI, lead text |
| `--text-xl` | 1.25rem | 20px | Títulos de sección (h3 en UI) |
| `--text-2xl` | 1.5rem | 24px | Headings de página (h2 en UI) |
| `--text-3xl` | 1.75rem | 28px | h1 en UI, h2 de artículo |
| `--text-4xl` | 2rem | 32px | Hero titles en Studio |
| `--text-5xl` | 2.625rem | 42px | h1 de artículo en `.prose` |
| `--text-6xl` | 3.5rem | 56px | Hero editorial / portada Magazine |

---

## Pesos y escala de emphasis

| Token CSS | Valor | Uso |
|---|---|---|
| `--weight-regular` | 400 | Cuerpo por defecto |
| `--weight-medium` | 500 | Énfasis suave, label de campo activo |
| `--weight-semibold` | 600 | Headings UI, columnas de tabla |
| `--weight-bold` | 700 | Headings de artículo `.prose`, strong |

---

## Interlineado (line-height)

| Token CSS | Valor | Uso |
|---|---|---|
| `--leading-tight` | 1.2 | Headings grandes, hero text |
| `--leading-snug` | 1.35 | Headings UI, títulos de card |
| `--leading-normal` | 1.5 | Body UI estándar |
| `--leading-relaxed` | 1.7 | Cuerpo de lectura larga — `.prose` a 68ch |

---

## Tracking (letter-spacing)

| Token CSS | Valor | Uso |
|---|---|---|
| `--tracking-tight` | -0.02em | Headings de display / hero |
| `--tracking-snug` | -0.01em | Headings de UI |
| `--tracking-normal` | 0 | Body, labels |
| `--tracking-wide` | 0.04em | Labels espaciados |
| `--tracking-caps` | 0.07em | Eyebrows en mayúsculas, badge labels |

---

## Los dos registros

### `.ax` — Studio UI

El registro del producto. Sans, compacto, funcional.

```css
.ax-root,
body.ax {
  font-family: var(--font-sans);
  font-size: var(--text-base);   /* 14px */
  line-height: var(--leading-normal);
  color: var(--text-body);
  background: var(--bg-canvas);
}

/* Headings en UI — sans, semibold */
.ax h1 { font-size: var(--text-3xl); letter-spacing: var(--tracking-tight); }
.ax h2 { font-size: var(--text-2xl); }
.ax h3 { font-size: var(--text-xl);  }
.ax h4 { font-size: var(--text-lg);  }
```

### `.prose` — Magazine editorial

El registro de contenido. Serif, generoso, académico.

```css
.prose {
  font-family: var(--font-serif);
  font-size: var(--text-md);      /* 16px */
  line-height: var(--leading-relaxed);  /* 1.7 */
  color: var(--ink-90);
  max-width: var(--measure);      /* 68ch */
  font-optical-sizing: auto;
}

/* Headings en artículo — serif, bold */
.prose h1 { font-size: var(--text-5xl); margin-top: 0; }
.prose h2 { font-size: var(--text-3xl); margin-top: 2em; }
.prose h3 { font-size: var(--text-xl);  margin-top: 1.6em; }
.prose h4 { font-size: var(--text-lg);  margin-top: 1.4em; font-weight: var(--weight-semibold); }
```

---

## Medida óptima de lectura

```css
--measure: 68ch;         /* Columna de lectura por defecto */
--measure-narrow: 58ch;  /* Columna estrecha */
```

La longitud de línea de 68 caracteres es la medida tipográfica recomendada para larga lectura. El contenido `.prose` siempre se centra en esta columna. No ajustar salvo diseño especial justificado.

---

## Casos de uso en componentes

### Button labels — sans, semibold, sentence case
```css
.btn {
  font-family: var(--font-sans);
  font-size: var(--text-base);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-normal);
}
```

### Badge labels — sans, semibold, caps con tracking
```css
.badge {
  font-family: var(--font-sans);
  font-size: var(--text-2xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
}
```

### Overlines / eyebrows — para secciones y cards
```css
.eyebrow {
  font-family: var(--font-sans);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-transform: uppercase;
  letter-spacing: var(--tracking-caps);
  color: var(--text-secondary);
}
```

### Código inline en artículo
```css
.prose code {
  font-family: var(--font-mono);
  font-size: 0.86em;
  background: var(--neutral-10);
  border: 1px solid var(--border-default);
  border-radius: var(--radius-sm);
  padding: 0.08em 0.36em;
  color: var(--blue-80);
}
```

---

## Casing

- **Sentence case** para headings y botones: `"Iniciar sesión"`, `"Ejecutar pipeline"`, `"Guardar cambios"`
- **UPPERCASE con tracking-caps** solo para eyebrows, overlines y labels de badge
- **Title Case** — evitar en UI y contenido en español

---

## Accesibilidad tipográfica

- Texto en `rem` — escala con el zoom del navegador al 200% sin ruptura de layout
- `--leading-relaxed` (1.7) para `.prose` — cumple WCAG 1.4.12
- No usar `!important` en `line-height` ni `letter-spacing` — respetar overrides del usuario
- `lang="es"` en el document root; cambiar `lang` en secciones de contenido en otro idioma
- Tamaño mínimo de body UI: `--text-base` (14px) — no bajar de 12px en ningún elemento funcional
