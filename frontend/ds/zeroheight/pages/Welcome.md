# Welcome to AlejandrIA Magazine Design System

> *Donde la ciencia rigurosa se encuentra con la publicación moderna y calmada.*

**AlejandrIA Magazine Design System** es la fuente única de verdad visual y de contenido para AlejandrIA Magazine — una plataforma editorial agentica donde investigadores y editores diseñan flujos de trabajo IA para crear, revisar, formatear y publicar artículos técnicos y científicos.

Este sistema define cómo se ve, se lee y se comporta todo lo que construimos: desde los botones del Studio hasta los artículos publicados en Magazine.

---

## Para quién es este sistema

### Diseñadores
Acceden a los fundamentos visuales (color, tipografía, espaciado, elevation), los patrones de componentes, y las guías de composición para las dos superficies del producto: **Studio** (interfaz de autoría agentica) y **Magazine** (capa de lectura editorial). Los tokens CSS se sincronizan con Figma via variables de color.

### Desarrolladores
Importan `colors_and_type.css` como fuente de tokens CSS, usan variables semánticas en sus componentes, y aplican clases `.ax` (UI) y `.prose` (contenido) para el registro tipográfico correcto. La librería de iconos es `lucide-react`.

### Product
Entienden los principios de diseño que guían las decisiones — Precisión y calma, Contenido primero, Accesibilidad por defecto — para que las conversaciones sobre nuevas funcionalidades partan de los mismos valores.

---

## Qué incluye este sistema

| Sección | Contenido |
|---|---|
| **Foundations** | Color, tipografía, espaciado, radius, elevation, motion |
| **Components** | Botones, inputs, badges, cards, modals, avatares, toggles, tabs |
| **Patterns** | Empty states, error handling, confirmaciones, estados de artículo |
| **Accessibility** | Normas WCAG 2.1 AA, diseño accesible, testing |
| **Content** | Voz y tono, copy de UI, mensajes de error, registro editorial |
| **Resources** | Código fuente, guías de instalación, release notes |

---

## Las dos superficies

AlejandrIA Magazine tiene dos modos visuales distintos pero coherentes:

**Studio** — El espacio de trabajo del investigador. Superficies blancas sobre canvas gris-azulado tenue, tipografía sans compacta, un azul de acción confiado. Dense de información, funcional, sin distracciones decorativas.

**Magazine** — La capa de lectura pública. Columna serif centrada a 68 caracteres, espacio generoso, ritmo tipográfico académico. Donde el artículo aprobado vive como publicación científica.

---

## Base técnica

Este sistema se construye sobre **Salesforce Lightning Design System 2 (SLDS2)** — estructura de tokens, escala de espaciado, jerarquía de color cloud — empujado hacia una estética editorial y científica. Añade lo que un kit de UI genérico no tiene: un sistema de contenido para autoría técnica y una capa de lectura para ciencia.

El archivo fuente es `colors_and_type.css`. Todo parte de ahí.

---

## Cómo navegar

Empieza por **Principles** para entender los valores que guían las decisiones de diseño. Luego explora **Color** y **Typography** para los fundamentos visuales. Los **Components** muestran los bloques de construcción concretos. **Accessibility** es vinculante — no opcional.
