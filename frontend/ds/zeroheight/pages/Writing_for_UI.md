# Writing for UI

Guía práctica de copy para la interfaz de Alexandria Magazine. Sentence case, verb-first, español, sin adornos.

---

## Botones y acciones

Los labels de botón son imperativos cortos. Verb-first, sentence case, sin artículo innecesario.

| Contexto | Correcto | Incorrecto |
|---|---|---|
| Guardar cambios | Guardar | Guardar los cambios |
| Ejecutar el pipeline | Ejecutar | Ejecutar el pipeline ahora |
| Publicar el artículo | Publicar | Click para publicar |
| Crear un artículo nuevo | Crear artículo | + Nuevo |
| Rechazar en revisión | Rechazar | Marcar como rechazado |
| Asignar revisor | Asignar revisor | Seleccionar un revisor |
| Volver a la lista | Volver | Ir atrás |
| Cancelar una acción | Cancelar | No, gracias |

---

## Labels de campo

Sentence case, sin dos puntos, sin verbos (el input ya implica acción).

```
✅ "Título del artículo"     ❌ "Título del artículo:"
✅ "Correo electrónico"      ❌ "Ingresa tu correo:"
✅ "Palabras clave"          ❌ "Palabras clave (separadas por coma)"
✅ "Formato de citación"     ❌ "¿En qué formato quieres citar?"
```

El texto de ayuda va debajo del campo, en `--text-muted`, nunca en el placeholder.

```jsx
<label htmlFor="palabras-clave">Palabras clave</label>
<input id="palabras-clave" placeholder="Escribe y presiona Enter" />
<p className="field-hint">Separa con Enter. Máximo 10 palabras clave.</p>
```

---

## Estados como sustantivos

Los nombres de estado son sustantivos, con primera mayúscula, exactos.

| Estado | Label |
|---|---|
| `draft` | Borrador |
| `in_review` | En revisión |
| `approved` | Aprobado |
| `published` | Publicado |
| `rejected` | Rechazado |

En badges, UPPERCASE con tracking: BORRADOR, APROBADO, PUBLICADO.

---

## Placeholders

Son pistas o ejemplos — nunca labels. Se desvanecen al escribir.

```
✅ placeholder="Escribe el título aquí"
✅ placeholder="ej. inteligencia artificial, revisión sistemática"
✅ placeholder="nombre@universidad.edu"

❌ placeholder="Título del artículo"  // ← este es el label, no el placeholder
```

---

## Mensajes de confirmación y feedback

Sin exclamaciones. Factual y breve.

| Situación | Mensaje |
|---|---|
| Guardado | "Flujo guardado" |
| Publicación | "Artículo publicado" |
| Asignación | "Revisor asignado" |
| Eliminación | "Artículo eliminado" |
| Ejecución completada | "Pipeline completado" |

El sujeto puede omitirse cuando el contexto es claro. "Flujo guardado" no necesita "Tu flujo se ha guardado correctamente."

---

## Textos de navegación y headings

Sentence case. Descriptivos del contenido de la página, no de las acciones.

```
✅ "Mis artículos"       ❌ "Ver mis artículos"
✅ "Flow Designer"       ❌ "Diseño de flujo"
✅ "Historial de cambios"  ❌ "Changelog"
✅ "Configuración"       ❌ "Ajustes y preferencias"
```

---

## Textos de empty state

Título: sustantivo o estado, `--text-secondary`. Descripción: qué puede hacer el usuario, `--text-muted`. CTA: imperativo.

```
Título:      "No hay artículos todavía"
Descripción: "Crea tu primer artículo para empezar a trabajar con el pipeline de agentes."
CTA:         "Crear artículo"
```

```
Título:      "Canvas vacío"
Descripción: "Arrastra agentes desde el panel izquierdo al canvas para crear tu flujo de trabajo."
CTA:         (ninguno — la descripción es la instrucción)
```

---

## Texto de carga / loading

Factual y en gerundio.

```
✅ "Cargando artículos..."
✅ "Ejecutando pipeline..."
✅ "Guardando cambios..."

❌ "Por favor espera..."
❌ "Esto puede tardar unos momentos..."
```

---

## Números y métricas

Exactos. Sin aproximaciones ni superlativos.

```
✅ "3 artículos"          ❌ "Algunos artículos"
✅ "Score 87/100"         ❌ "Alta puntuación"
✅ "Mínimo 6 caracteres"  ❌ "La contraseña debe ser segura"
✅ "Última edición: hoy a las 14:32"  ❌ "Editado hace poco"
```

---

## Tooltips

Tooltips para iconos sin label o acciones cuyo nombre no cabe en el espacio. Máximo 2 líneas. Sin punto final si es una frase corta.

```
✅ "Guardar como borrador"
✅ "Copiar enlace del artículo"
✅ "Ejecutar solo este agente"
❌ "Haz clic aquí para guardar el artículo como borrador."
```
