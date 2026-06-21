# Error Messages

Los mensajes de error de Alexandria Magazine son directos, sin culpar al usuario, y siempre accionables. El formato es consistente: qué pasó + qué puede hacer el usuario.

---

## El formato

```
[Qué pasó.] [Qué puede hacer el usuario.]
```

- **Qué pasó:** específico, sin términos internos de sistema ("Error 500", "Exception null pointer")
- **Qué puede hacer:** una acción concreta, no vaga ("intenta de nuevo", no "contacta soporte")
- **Tono:** primera persona del sistema, no del usuario. "No se pudo guardar" no "No guardaste".

---

## Ejemplos por tipo

### Errores de red / conexión

```
✅ "No se pudo guardar el artículo. Verifica tu conexión e intenta de nuevo."
✅ "No se pudo cargar el flujo. Recarga la página o intenta más tarde."
✅ "Sin conexión. Los cambios se guardarán automáticamente cuando se restablezca."

❌ "Error de red"
❌ "Error desconocido"
❌ "¡Ups! Algo salió mal 😔"
❌ "Network request failed with status 503"
```

### Errores de validación de formulario

```
✅ "El título no puede estar vacío."
✅ "El correo electrónico no es válido. Usa el formato nombre@dominio.com."
✅ "La contraseña debe tener mínimo 6 caracteres."
✅ "Ya existe un flujo con este nombre. Elige un nombre diferente."

❌ "Campo requerido"
❌ "Input inválido"
❌ "Error en el campo"
```

### Errores de agente en pipeline

```
✅ "El agente Investigador no pudo acceder a la fuente RAG. Verifica la configuración de Qdrant."
✅ "El agente Redactor tardó más de lo esperado. El pipeline se detuvo. Intenta ejecutarlo de nuevo."
✅ "Sin resultados del agente Revisor. El documento puede estar vacío."

❌ "Agent failed"
❌ "Error en el pipeline"
❌ "Timeout"
```

### Errores de permisos

```
✅ "No tienes permisos para aprobar este artículo. Solicita acceso al propietario."
✅ "Esta acción requiere rol de editor. Contacta al administrador del espacio."

❌ "Acceso denegado"
❌ "403 Forbidden"
```

### Errores de carga de datos

```
✅ "No se pudieron cargar los artículos. Recarga la página."
✅ "No se pudo cargar el historial de cambios. Intenta más tarde."

❌ "Error 500"
❌ "Failed to fetch"
```

---

## Reglas de copy de error

| Regla | Correcto | Incorrecto |
|---|---|---|
| Específico, no genérico | "No se pudo guardar el flujo" | "Error desconocido" |
| Accionable | "Verifica tu conexión e intenta de nuevo" | "Por favor intenta más tarde" |
| Sin culpar al usuario | "No se pudo validar el correo" | "Ingresaste un correo inválido" |
| Sin jerga técnica | "No se pudo guardar" | "Request failed with 422" |
| Sin exclamaciones ni emoji | "Algo salió mal." | "¡Oops! 😬" |
| Sentence case | "El título no puede estar vacío." | "El Título No Puede Estar Vacío." |
| Punto final en mensajes completos | "Verifica tu conexión." | "Verifica tu conexión" |

---

## Errores en campo vs. errores en toast

| Tipo de error | Patrón | Cuándo usarlo |
|---|---|---|
| Validación de campo | Inline, debajo del input | El usuario envió el formulario o el campo perdió foco |
| Error de operación | Toast rojo auto-dismiss | Guardado fallido, error de pipeline, error de red |
| Error de sistema | Alerta inline en página | Error de carga de datos, sin conexión, mantenimiento |
| Error modal | Modal de error | Cuando el error bloquea toda la acción y requiere decisión |

---

## Errores de pipeline — nivel de detalle

Los errores de agente deben ser lo suficientemente específicos para que el usuario sepa qué revisar, pero sin exponer stack traces o mensajes técnicos raw del sistema.

```jsx
// Mensaje de error de agente — capa de presentación
const agentErrorMessages = {
  'qdrant_connection': 'El agente no pudo acceder a la fuente RAG. Verifica la configuración de Qdrant.',
  'ollama_timeout':    'El modelo de lenguaje tardó demasiado. Intenta con un artículo más corto o repite la ejecución.',
  'empty_document':    'El artículo está vacío. Agrega contenido antes de ejecutar el pipeline.',
  'review_threshold':  'El score de aprobación no alcanzó el umbral mínimo (60). Revisa las observaciones del Revisor.',
};
```

El stack trace y el error técnico van a logs de desarrollo — nunca al usuario.

---

## Accesibilidad en mensajes de error

```jsx
{/* Error de campo — aria-describedby + aria-invalid */}
<input
  id="titulo"
  aria-invalid={hasError}
  aria-describedby={hasError ? "titulo-error" : undefined}
/>
{hasError && (
  <div id="titulo-error" role="alert" className="field-error">
    <AlertCircle size={14} aria-hidden="true" />
    El título no puede estar vacío.
  </div>
)}

{/* Toast de error — role="alert" para anuncio inmediato */}
<div role="alert" aria-live="assertive" className="toast-error">
  <XCircle size={18} aria-hidden="true" />
  No se pudo guardar el flujo. Verifica tu conexión.
</div>
```
