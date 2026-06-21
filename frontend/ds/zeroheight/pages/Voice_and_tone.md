# Voice & Tone

Alexandria Magazine es una herramienta para científicos. La voz del producto es **precisa, calmada y creíble** — la misma voz de un buen paper académico, adaptada al contexto de una herramienta de trabajo.

---

## La voz de Alexandria

**Precisa.** No hay espacio para ambigüedad en un pipeline de publicación científica. Las acciones se llaman por su nombre exacto. Los estados del artículo tienen nombres de dominio, no eufemismos.

**Calmada.** Sin exclamaciones. Sin celebración exagerada. El usuario sabe lo que hizo — solo necesita confirmación de que ocurrió. "Flujo guardado", no "¡Tu flujo se guardó exitosamente! 🎉".

**Creíble.** El vocabulario técnico exacto. Nunca suavizar términos del dominio para parecer más amigable. "Score de aprobación", no "puntuación". "Pipeline", no "proceso". "RAG", no "tu base de conocimiento".

---

## Español-first

El producto es **español-first**. Toda la interfaz de usuario está en español. El contenido científico puede estar en cualquier idioma (según el idioma del investigador), pero el chrome — navegación, botones, mensajes, estados, toasts — es siempre en español.

```
✅ "Iniciar sesión"     ❌ "Sign in"
✅ "Ejecutar pipeline"  ❌ "Run pipeline"
✅ "Borrador"           ❌ "Draft"
✅ "Flujo guardado"     ❌ "Flow saved"
```

---

## Segunda persona — "tú" informal

Warm, pero no familiar en exceso. Directo e incluido en la tarea.

```
✅ "Diseña tu pipeline"
✅ "Arrastra agentes desde el panel izquierdo al canvas"
✅ "¿No tienes cuenta?"
✅ "Asigna un revisor para continuar"
```

---

## Imperativos para acciones

Labels de botón verb-first, sentence case, sin artículo.

```
✅ "Guardar"           ❌ "Guardar cambios ahora"
✅ "Ejecutar"          ❌ "Click aquí para ejecutar"
✅ "Aprobar"           ❌ "Marcar como aprobado"
✅ "Rechazar"          ❌ "Denegar solicitud"
✅ "Crear artículo"    ❌ "Nuevo artículo"
✅ "Asignar revisor"   ❌ "Seleccionar revisor"
```

---

## Casing

| Contexto | Regla | Ejemplo |
|---|---|---|
| Headings de página | Sentence case | "Mis artículos" |
| Botones | Sentence case | "Ejecutar pipeline" |
| Labels de campo | Sentence case | "Título del artículo" |
| Nombres de estado | Sustantivo, primera mayúscula | "Borrador", "En revisión", "Aprobado" |
| Badge labels | UPPERCASE + tracking | "APROBADO", "EN REVISIÓN" |
| Eyebrows / overlines | UPPERCASE + tracking | "ARTÍCULOS RECIENTES" |
| Title Case | Evitar | — |

---

## Vocabulario de dominio

El vocabulario técnico es exacto. No suavizar ni reemplazar por términos genéricos.

| Término correcto | Incorrecto | Contexto |
|---|---|---|
| Artículo | Documento, post | El objeto que se crea y publica |
| Borrador | Draft, borrador preliminar | Estado inicial del artículo |
| Pipeline | Proceso, flujo de trabajo genérico | La cadena de agentes IA |
| Flujo | — | La instancia del pipeline diseñada en el canvas |
| Agente | Bot, asistente | Cada nodo del pipeline |
| Score de aprobación | Puntuación, calificación | El 0-100 del revisor |
| RAG | Base de conocimiento | Retrieval-augmented generation |
| Revisor | Evaluador | El rol que aprueba/rechaza |
| Formato | Estilo de cita | APA, IEEE, Vancouver |

---

## Sin emoji en UI

El producto no usa emoji en la interfaz. Los estados, alertas y confirmaciones usan iconos Lucide. Los documentos internos (READMEs, comentarios de código) pueden tenerlos.

```
✅ <CheckCircle size={14} /> Aprobado
❌ ✅ Aprobado

✅ "Flujo guardado"
❌ "Flujo guardado ✨"
```

---

## Números y datos factuales

Los números en el producto son exactos, sin aproximaciones.

```
✅ "3 artículos en total"          ❌ "Algunos artículos"
✅ "Score 87/100"                  ❌ "Buen score"
✅ "Mínimo 6 caracteres"           ❌ "La contraseña es corta"
✅ "Pipeline completado en 2m 14s" ❌ "Pipeline completado rápidamente"
```

---

## Dos registros — UI vs. contenido publicado

La voz de la interfaz (Spanish-first, tú, imperativo) es diferente de la voz del contenido científico publicado.

**UI:** directo, funcional, segunda persona
> "Arrastra agentes al canvas para crear tu flujo."

**Artículo publicado:** tercera persona académica, medido, orientado a evidencia
> "Los resultados demuestran una mejora estadísticamente significativa en F1-score (p < 0.01)."

Nunca mezclar los registros. Los mensajes de UI nunca suenan como un abstract; el contenido científico nunca suena como un botón.
