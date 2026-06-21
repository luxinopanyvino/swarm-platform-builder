# Content

El sistema de contenido de Alexandria Magazine define dos registros escritos distintos: el **copy de UI** (interfaz del Studio) y la **prosa del artículo** (contenido científico publicado en Magazine). Son voces diferentes que coexisten en la misma plataforma.

---

## Dos registros

### Studio UI copy

La voz del producto. Español-first, segunda persona, imperativo, sentence case. El chrome de la aplicación habla al usuario directamente sobre lo que puede hacer.

**Características:**
- Español siempre
- "tú" informal, directo
- Verbos imperativos para acciones
- Vocabulario técnico exacto del dominio
- Sin exclamaciones, sin emoji
- Sentence case en todo
- Números factuales

**Ejemplos del producto:**
> "Arrastra agentes desde el panel izquierdo al canvas para crear tu flujo de trabajo."
> "Usa @ para mencionar al revisor."
> "Se creará un nuevo artículo y se ejecutará el pipeline sobre él."
> "Plataforma inteligente para crear, revisar y publicar artículos científicos con agentes IA."

### Prosa del artículo científico

La voz del investigador. Tercera persona, académica, medida, orientada a evidencia. El artículo publicado en Magazine tiene su propia voz — la del autor.

**Características:**
- Cualquier idioma (según el autor)
- Tercera persona académica
- Tono medido, sin valoraciones subjetivas
- Terminología técnica del campo
- Referencias y citas formateadas (APA/IEEE/Vancouver)
- Estructura: abstract → keywords → secciones → conclusiones → referencias

---

## Estructura de un artículo en Magazine

```
Título                    ← Source Serif 4, --text-5xl
Abstract                  ← .prose, párrafo introductorio
Palabras clave            ← chips de tag, --text-sm
─────────────────────────
Sección 1                 ← h2
  Subsección 1.1          ← h3
  Fig. 1 + caption        ← figcaption con .fig-label
Sección 2
  Tabla 1                 ← .prose table
  Ecuación
─────────────────────────
Nota / Metodología / Hallazgo clave  ← callout blocks
─────────────────────────
Conclusiones
Referencias               ← APA / IEEE / Vancouver
```

---

## Callouts del artículo

Tres tipos de callout para destacar contenido dentro del artículo:

```html
<!-- Nota informativa -->
<aside class="callout callout-note">
  <strong>Nota</strong>
  <p>Los datos presentados corresponden a una muestra de 2.847 artículos publicados entre 2020 y 2024.</p>
</aside>

<!-- Metodología -->
<aside class="callout callout-method">
  <strong>Metodología</strong>
  <p>Se empleó revisión sistemática según PRISMA 2020 con búsqueda en PubMed, Scopus y Web of Science.</p>
</aside>

<!-- Hallazgo clave -->
<aside class="callout callout-finding">
  <strong>Hallazgo clave</strong>
  <p>Los modelos con fine-tuning de dominio superaron el baseline en 23.4 puntos de F1-score (p &lt; 0.001).</p>
</aside>
```

```css
.callout {
  padding: var(--space-md) var(--space-lg);
  border-left: 3px solid;
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  font-family: var(--font-sans);
  font-size: var(--text-sm);
}

.callout-note    { border-color: var(--info);    background: var(--info-bg);    }
.callout-method  { border-color: var(--accent);  background: var(--accent-tint); }
.callout-finding { border-color: var(--success); background: var(--success-bg); }
```

---

## Figuras y captions

```html
<figure>
  <img src="fig-1-results.png" alt="Comparación de F1-score entre modelos baseline y fine-tuned" />
  <figcaption>
    <span class="fig-label">Fig. 1.</span>
    Comparación de rendimiento entre el modelo baseline GPT-4 y la versión con fine-tuning de dominio.
    Las barras de error representan ± 1 desviación estándar (n = 5 runs).
  </figcaption>
</figure>
```

`.fig-label` en `--blue-60`, `font-weight: semibold`. Caption en `--text-secondary`, `--text-sm`, sans.

---

## Formato de referencias

Los agentes Formateador y Publicador manejan el formato de referencias automáticamente. Los formatos soportados son APA, IEEE y Vancouver. El investigador solo declara el formato preferido en la configuración del artículo.

```
APA:     Apellido, N. (Año). Título del artículo. Revista, Volumen(Número), pp–pp.
IEEE:    N. Apellido, "Título del artículo," Revista, vol. X, no. Y, pp. pp–pp, Año.
Vancouver: Apellido N. Título del artículo. Revista. Año;Vol(Num):pp-pp.
```

---

→ Ver **Voice & Tone** para la voz del copy de UI.
→ Ver **Writing for UI** para patrones concretos de labels, botones y mensajes.
→ Ver **Error Messages** para el formato de mensajes de error.
