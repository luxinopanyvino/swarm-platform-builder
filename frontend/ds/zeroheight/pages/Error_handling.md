# Error Handling

Los errores en Alexandria Magazine son directos, sin culpar al usuario, y siempre en texto más icono. Nunca solo color. El objetivo es darle al usuario exactamente lo que necesita para continuar.

---

## Tres patrones de error

### 1. Errores inline — en formularios

Aparecen debajo del campo cuando la validación falla. El campo adquiere borde `--error`, el mensaje aparece en texto `--error` con icono `alert-circle` de Lucide.

```jsx
<div className="form-field">
  <label htmlFor="titulo">Título del artículo</label>
  <input
    id="titulo"
    className="input"
    aria-invalid={hasError}
    aria-describedby={hasError ? "titulo-error" : undefined}
  />
  {hasError && (
    <div id="titulo-error" className="field-error" role="alert">
      <AlertCircle size={14} />
      El título no puede estar vacío.
    </div>
  )}
</div>
```

```css
.field-error {
  display: flex;
  align-items: center;
  gap: var(--space-2xs);
  color: var(--error);
  font-size: var(--text-sm);
  margin-top: var(--space-xs);
}

.input[aria-invalid="true"] {
  border-color: var(--error);
  box-shadow: 0 0 0 1px var(--error);
}
```

### 2. Alertas — mensajes de error en página

Para errores de sistema o de contexto más amplio (error al cargar datos, problema de conexión). Aparecen en línea dentro del contenido.

```css
.alert-error {
  display: flex;
  align-items: flex-start;
  gap: var(--space-sm);
  background: var(--error-bg);
  border: 1px solid var(--error);
  border-left: 3px solid var(--error);
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  color: var(--text-heading);
}

.alert-error .alert-icon {
  color: var(--error);
  flex-shrink: 0;
  margin-top: 1px;
}
```

```jsx
<div className="alert-error" role="alert">
  <AlertCircle size={18} className="alert-icon" />
  <div>
    <strong>No se pudo cargar el artículo.</strong>
    <p>Verifica tu conexión e intenta de nuevo.</p>
  </div>
</div>
```

### 3. Toasts de error — notificaciones transitorias

Para errores de operaciones en background (guardado fallido, error de agente, problema de red). Aparecen en la esquina superior derecha, auto-dismiss a los 6s, descartables manualmente.

```css
.toast-error {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  background: var(--error);
  color: #ffffff;
  border-radius: var(--radius-md);
  padding: var(--space-sm) var(--space-md);
  box-shadow: var(--shadow-3);
  min-width: 280px;
  max-width: 400px;
}
```

```jsx
// Implementación con aria-live para anuncio en screen readers
<div aria-live="assertive" aria-atomic="true">
  {errorToast && (
    <div className="toast-error" role="alert">
      <XCircle size={18} />
      <span>No se pudo guardar el flujo.</span>
      <button aria-label="Cerrar" onClick={dismiss}>
        <X size={14} />
      </button>
    </div>
  )}
</div>
```

---

## Reglas de error handling

### Siempre texto + icono
El color solo nunca es suficiente. Cada estado de error tiene:
- **Color** `--error` / `--error-bg`
- **Icono** Lucide: `alert-circle` (advertencia), `x-circle` (fallo), `wifi-off` (conexión)
- **Texto** explicativo — qué pasó y qué hacer

### Formato del mensaje
```
✅ Correcto:
"No se pudo guardar el artículo. Verifica tu conexión e intenta de nuevo."

❌ Incorrecto:
"Error 500"
"Error desconocido"
"Algo salió mal"
"¡Oops! No pudimos procesar tu solicitud 😔"
```

Estructura recomendada: **[qué pasó]** + **[qué puede hacer el usuario]**.

### Asociación semántica en formularios
```jsx
// aria-describedby vincula el campo con su mensaje de error
<input
  aria-invalid="true"
  aria-describedby="field-error-id"
/>
<div id="field-error-id" role="alert">
  {errorMessage}
</div>
```

### Toasts de error — duración
- Auto-dismiss: 6 segundos (más largo que success por la acción requerida)
- Pausa el timer en hover
- Siempre descartable manualmente
- `role="alert"` para anuncio inmediato en screen readers (no polite)

---

## Errores de agente en el Flow Designer

Cuando un agente falla durante la ejecución del pipeline, el nodo muestra un estado de error con:
- Borde izquierdo `--error` en el nodo
- Icono `x-circle` en el header del nodo
- Badge `--error` con label "Error"
- Mensaje expandible con el error del agente

```jsx
<AgentNode
  status="error"
  errorMessage="El agente no pudo acceder a la fuente RAG. Verifica la configuración de Qdrant."
/>
```

---

## No hacer

- No usar `alert()` del navegador — siempre UI inline o toast
- No solo cambiar el color de un borde sin mensaje de texto
- No errores genéricos ("Algo salió mal") — ser específico
- No errores que culpen al usuario ("Cometiste un error en...")
- No celebrar la recuperación del error con animaciones
