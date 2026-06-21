# Empty States

Los empty states de Alexandria Magazine son minimalistas, directos, y siempre orientados a la siguiente acción. Sin ilustraciones generadas, sin ilustraciones de stock, sin decoración excesiva.

---

## Anatomía de un empty state

```
[Icono tile]          ← Lucide 24-28px en tile con tint brand/neutral
[Título]              ← --text-secondary, --text-xl, sans semibold
[Descripción corta]   ← --text-muted, --text-base, una o dos líneas
[CTA opcional]        ← btn-primary o btn-secondary, solo si hay acción clara
```

---

## Implementación

```jsx
import { FileText, Plus } from 'lucide-react';

<div className="empty-state">
  <div className="empty-state-icon">
    <FileText size={28} />
  </div>
  <h3 className="empty-state-title">No hay artículos todavía</h3>
  <p className="empty-state-description">
    Crea tu primer artículo para empezar a trabajar con el pipeline de agentes.
  </p>
  <button className="btn btn-primary btn-base">
    <Plus size={16} />
    Crear artículo
  </button>
</div>
```

```css
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--space-3xl) var(--space-xl);
  gap: var(--space-sm);
}

.empty-state-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  background: var(--brand-tint);   /* --blue-05 */
  color: var(--brand);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-xs);
}

.empty-state-title {
  font-size: var(--text-xl);
  font-weight: var(--weight-semibold);
  color: var(--text-secondary);
  margin: 0;
}

.empty-state-description {
  font-size: var(--text-base);
  color: var(--text-muted);
  max-width: 360px;
  margin: 0;
  line-height: var(--leading-normal);
}

.empty-state .btn {
  margin-top: var(--space-md);
}
```

---

## Variantes por contexto

### Lista de artículos vacía

```jsx
<EmptyState
  icon={<FileText size={28} />}
  title="No hay artículos todavía"
  description="Crea tu primer artículo para empezar a trabajar con el pipeline de agentes."
  action={
    <button className="btn btn-primary btn-base">
      <Plus size={16} />
      Crear artículo
    </button>
  }
/>
```

### Flujo de trabajo vacío

```jsx
<EmptyState
  icon={<GitBranch size={28} />}
  title="Canvas vacío"
  description="Arrastra agentes desde el panel izquierdo al canvas para crear tu flujo de trabajo."
/>
// Sin CTA — la instrucción es la acción
```

### Sin resultados de búsqueda

```jsx
<EmptyState
  icon={<Search size={28} />}
  title="Sin resultados"
  description={`No se encontraron artículos para "${query}". Prueba con otros términos.`}
  action={
    <button className="btn btn-ghost btn-base" onClick={clearSearch}>
      Limpiar búsqueda
    </button>
  }
/>
```

### Sin acceso / permiso

```jsx
<EmptyState
  icon={<Shield size={28} />}
  title="Sin acceso"
  description="No tienes permisos para ver este artículo. Solicita acceso al propietario."
/>
// Sin CTA — no hay acción disponible para el usuario
```

### Resultados de pipeline vacíos

```jsx
<EmptyState
  icon={<Bot size={28} />}
  title="Pipeline no ejecutado"
  description="Ejecuta el pipeline para ver los resultados de los agentes aquí."
  action={
    <button className="btn btn-primary btn-base">
      <Zap size={16} />
      Ejecutar pipeline
    </button>
  }
/>
```

---

## Iconos por tipo de contenido

| Contexto | Icono Lucide | Tint de icon tile |
|---|---|---|
| Lista de artículos vacía | `file-text` | `--brand-tint` (azul) |
| Canvas de flujo vacío | `git-branch` | `--brand-tint` (azul) |
| Sin resultados de búsqueda | `search` | `--bg-inset` (neutro) |
| Sin acceso | `shield` | `--bg-inset` (neutro) |
| Agente sin resultados | `bot` | `--accent-tint` (violeta) |
| Sin revisores asignados | `user-plus` | `--bg-inset` (neutro) |
| RAG sin documentos | `book-open` | `--brand-tint` (azul) |

---

## Reglas

- **Icono:** Lucide, 24–28px, en tile de 48–56px con tint como fondo
- **Título:** `--text-xl`, `--weight-semibold`, `--text-secondary` — nunca `--text-heading` para que no compita con headings de página
- **Descripción:** `--text-base`, `--text-muted`, máximo 2 líneas, máximo 360px de ancho
- **CTA:** Opcional — solo si hay una acción obvia y directa. No inventar acciones solo por tener un botón.
- **Sin ilustraciones generadas** — nunca imágenes de stock, nunca SVG decorativo complejo, nunca art generado por IA
- **Sin emoji** en títulos ni descripciones de empty states
- **Centrado vertical** solo en vistas donde el empty state ocupa la pantalla completa; en paneles secundarios, alinear al tope con padding
