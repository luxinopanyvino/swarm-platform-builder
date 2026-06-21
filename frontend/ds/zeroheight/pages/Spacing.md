# Spacing

El sistema de espaciado de Alexandria Magazine usa una **base de 4px** con una escala rem alineada a SLDS. Todos los márgenes, paddings y gaps se componen exclusivamente de estos tokens — nunca valores arbitrarios en px.

---

## La escala completa

| Token CSS | rem | px | Uso típico |
|---|---|---|---|
| `--space-3xs` | 0.125rem | **2px** | Nudges de alineación, separadores de hairline |
| `--space-2xs` | 0.25rem | **4px** | Padding de badge, gap icono-texto pequeño |
| `--space-xs` | 0.5rem | **8px** | Gap estándar icono-label, padding de toolbar |
| `--space-sm` | 0.75rem | **12px** | Padding de nav item, gap de form field |
| `--space-md` | 1rem | **16px** | Padding de card compacta, separación de sección |
| `--space-lg` | 1.5rem | **24px** | **Padding de card por defecto**, column gap |
| `--space-xl` | 2rem | **32px** | Separación entre secciones |
| `--space-2xl` | 3rem | **48px** | Separadores mayores entre bloques |
| `--space-3xl` | 4rem | **64px** | Padding vertical de página |
| `--space-4xl` | 5rem | **80px** | Ritmo vertical de hero editorial |

---

## Reglas de composición

### Espaciado de cards

```css
.card {
  padding: var(--space-lg);           /* 24px — default */
  border-radius: var(--radius-lg);    /* 12px */
}

.card-compact {
  padding: var(--space-md);           /* 16px — versión compacta */
}

.card-header {
  padding: var(--space-md) var(--space-lg);  /* 16px arriba/abajo, 24px lados */
  border-bottom: 1px solid var(--border-default);
}
```

### Espaciado en formularios

```css
.form-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);               /* 8px — label → input */
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);               /* 16px — entre campos */
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-xl);               /* 32px — entre grupos de campos */
}
```

### Gap en listas y grids

```css
.article-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);               /* 12px — lista compacta */
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-lg);               /* 24px — grid de cards */
}
```

---

## Layout del shell de la app

El shell de Studio tiene dimensiones fijas que no cambian con el espaciado de contenido:

| Constante | Token CSS | Valor | Descripción |
|---|---|---|---|
| Sidebar | `--sidebar-w` | 248px | Panel lateral de navegación izquierdo |
| Topbar | `--topbar-h` | 56px | Barra superior de la app |

```css
/* Layout del shell */
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) 1fr;
  grid-template-rows: var(--topbar-h) 1fr;
  min-height: 100vh;
}

.app-topbar {
  grid-column: 1 / -1;
  height: var(--topbar-h);
  background: var(--bg-shell);
  border-bottom: 1px solid var(--border-default);
  padding: 0 var(--space-lg);         /* 24px horizontal */
}

.app-sidebar {
  width: var(--sidebar-w);
  background: var(--bg-shell);
  border-right: 1px solid var(--border-default);
  padding: var(--space-md) 0;         /* 16px vertical */
}

.app-content {
  background: var(--bg-canvas);
  padding: var(--space-xl) var(--space-2xl);  /* 32px arriba, 48px lados */
  overflow-y: auto;
}
```

---

## Espaciado de navegación

```css
.nav-item {
  padding: var(--space-xs) var(--space-md);   /* 8px 16px */
  border-radius: var(--radius-md);
  gap: var(--space-xs);                        /* 8px icono-texto */
}

.nav-section-label {
  padding: var(--space-sm) var(--space-md);   /* 12px 16px */
  margin-top: var(--space-xs);
}
```

---

## Columna de lectura editorial

```css
.reading-column {
  max-width: var(--measure);          /* 68ch */
  margin: 0 auto;
  padding: var(--space-3xl) var(--space-lg);  /* 64px arriba, 24px lados */
}
```

---

## Principios de espaciado

1. **Solo tokens.** Nunca valores arbitrarios (`margin: 17px` es señal de error). Si necesitas un valor intermedio, revisa si el diseño puede ajustarse al token más cercano.
2. **Componer de la escala 4px.** El sistema ya incluye múltiplos de 4: 4, 8, 12, 16, 24, 32, 48, 64, 80. Esto cubre casi todos los casos.
3. **Densidad por contexto.** Toolbar y tablas usan `xs/sm`; cards y formularios usan `md/lg`; secciones de página usan `xl/2xl`.
4. **Padding de card** es `lg` (24px) por defecto. `md` (16px) para cards compactas o listas densas.
5. **Column gaps** entre columnas del grid: `lg` (24px).
6. **Gap icono-label** en botones, nav, y controles: siempre `xs` (8px).

---

## Espaciado en React

```jsx
// Usando CSS custom properties directamente en estilos inline
<div style={{ padding: 'var(--space-lg)', gap: 'var(--space-md)' }}>

// O con clases CSS de utilidad si el proyecto las tiene
<Card className="p-lg">
  <div className="flex gap-xs items-center">
    <Search size={16} />
    <span>Buscar artículos</span>
  </div>
</Card>
```
