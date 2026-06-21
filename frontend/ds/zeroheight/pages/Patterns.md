# Patterns

Los patrones de UX de Alexandria Magazine son soluciones recurrentes a problemas de diseño específicos del producto: un workspace de autoría agentica donde el estado de los artículos, los errores de pipeline y las confirmaciones de flujo son interacciones de primera clase.

---

## Índice de patrones

| Patrón | Descripción |
|---|---|
| **Empty states** | Pantallas sin contenido — vacío inicial, sin resultados, sin acceso |
| **Error handling** | Errores inline, alertas de sistema, toasts de error |
| **Confirmation & success** | Toasts de éxito, badges de estado, confirmación de publicación |
| **Estado del artículo** | Ciclo completo borrador → publicado |
| **Loading / skeleton** | Estados de carga y espera |

---

## Patrón: Estado del artículo

El artículo científico en Alexandria pasa por un ciclo de vida estricto. Este ciclo se representa visualmente en toda la interfaz.

```
Borrador → En revisión → Aprobado → Publicado
                     ↓
                  Rechazado
```

| Estado | Badge | Color | Icono |
|---|---|---|---|
| Borrador | `Borrador` | `--status-draft` (gris) | `clock` |
| En revisión | `En revisión` | `--status-review` (amber) | `eye` |
| Aprobado | `Aprobado` | `--status-approved` (verde) | `check-circle` |
| Publicado | `Publicado` | `--status-published` (azul) | `send` |
| Rechazado | `Rechazado` | `--status-rejected` (rojo) | `x-circle` |

Siempre: color + etiqueta + icono. Nunca solo color.

---

## Patrón: Loading y skeleton

Para estados de carga de datos, usar skeletons (placeholder animado) en vez de spinners para listas y cards. Spinners para acciones puntuales (botón en loading, ejecución de agente).

```css
/* Skeleton */
.skeleton {
  background: linear-gradient(
    90deg,
    var(--bg-inset) 25%,
    var(--bg-hover) 50%,
    var(--bg-inset) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

@keyframes shimmer {
  0%   { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton {
    animation: none;
    background: var(--bg-inset);
  }
}
```

---

## Patrón: Confirmación de acción destructiva

Antes de eliminar un artículo o flujo, mostrar un modal de confirmación. No un `window.confirm()` — un modal propio del sistema.

```jsx
<Modal open={confirmDelete} onClose={() => setConfirmDelete(false)}>
  <Modal.Header>
    <h2>Eliminar artículo</h2>
  </Modal.Header>
  <Modal.Body>
    <p>
      ¿Eliminar <strong>"{article.title}"</strong>?
      Esta acción no se puede deshacer.
    </p>
  </Modal.Body>
  <Modal.Footer>
    <button className="btn btn-ghost btn-base" onClick={cancel}>
      Cancelar
    </button>
    <button className="btn btn-danger btn-base" onClick={confirm}>
      <Trash2 size={16} />
      Eliminar artículo
    </button>
  </Modal.Footer>
</Modal>
```

El botón de confirmación es `btn-danger` con label verb-first: "Eliminar artículo", no "Sí" ni "Confirmar".

---

## Patrón: Feedback de ejecución de pipeline

Cuando el usuario ejecuta un pipeline de agentes, cada nodo muestra su estado en tiempo real:

| Estado del nodo | Visual |
|---|---|
| Pendiente | Borde `--border-default`, sin badge |
| Ejecutando | Borde `--brand`, spinner `--brand`, badge "Ejecutando" azul |
| Completado | Borde izquierdo `--success`, badge "Completado" verde |
| Error | Borde izquierdo `--error`, badge "Error" rojo, mensaje expandible |

---

## Patrón: Score de aprobación

El score de aprobación (0–100) es un número factual. Se muestra en el header del artículo post-pipeline.

```jsx
<div className="approval-score">
  <span className="score-label">Score de aprobación</span>
  <span className="score-value" style={{
    color: score >= 80 ? 'var(--success)' :
           score >= 60 ? 'var(--warning)' :
                         'var(--error)'
  }}>
    {score}/100
  </span>
</div>
```

Regla: score ≥ 80 verde, 60–79 amber, < 60 rojo. Siempre número + texto — nunca barra de progreso sola.

---

Ver páginas específicas: **Empty states**, **Error handling**, **Confirmation & success**.
