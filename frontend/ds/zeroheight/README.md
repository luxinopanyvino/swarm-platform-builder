# Zeroheight Package — AlexandrIA Magazine Design System

Paquete de contenido para poblar el styleguide de Zeroheight del Design System de Alexandria Magazine.

**Styleguide:** https://sanmartineme.zeroheight.com/styleguide/s/143429/

---

## Contenido del paquete

```
zeroheight/
├── README.md                          ← Este archivo
├── tokens.dtcg.json                   ← Tokens en formato W3C DTCG
├── upload_tokens.sh                   ← Script de carga via API
└── pages/
    ├── Welcome.md
    ├── Principles.md
    ├── Getting_started.md
    ├── Color.md
    ├── Typography.md
    ├── Spacing.md
    ├── Tokens.md
    ├── Foundations.md
    ├── Button.md
    ├── Components.md
    ├── Error_handling.md
    ├── Confirmation_success.md
    ├── Empty_states.md
    ├── Patterns.md
    ├── Accessibility_standards.md
    ├── Designing_for_accessibility.md
    ├── Testing_accessibility.md
    ├── Accessibility.md
    ├── Voice_and_tone.md
    ├── Writing_for_UI.md
    ├── Error_messages.md
    ├── Content.md
    ├── Design.md
    ├── Code.md
    ├── Release_notes.md
    └── Resources.md
```

---

## Cómo usar este paquete

### 1. Tokens (automático via API)

Los tokens de `tokens.dtcg.json` se cargan via el script de shell:

```bash
# Obtén tu API key en: https://zeroheight.com/settings/api
export ZH_API_KEY="zh_tu_api_key_aqui"
bash upload_tokens.sh
```

El script verifica la conexión, carga el archivo DTCG y confirma el resultado.

**Alternativa manual:** En Zeroheight, ir a la página **Tokens** → sección de design tokens → importar `tokens.dtcg.json`.

---

### 2. Contenido de páginas (copiar-pegar manual)

Cada archivo en `pages/` corresponde a una página del styleguide de Zeroheight. El flujo es:

1. Abrir Zeroheight en el editor de la página correspondiente
2. Abrir el archivo `.md` de la página
3. Copiar el contenido markdown
4. En el editor de Zeroheight, agregar un bloque de tipo **"Rich text"** o **"Markdown"**
5. Pegar el contenido

> Zeroheight renderiza markdown estándar: headings, tablas, listas, y bloques de código con syntax highlighting.

---

## Mapa de páginas → archivos

| Página en Zeroheight | ID | Archivo |
|---|---|---|
| Welcome | 8667521 | `pages/Welcome.md` |
| Principles | 8667522 | `pages/Principles.md` |
| Getting started | 8667523 | `pages/Getting_started.md` |
| Color | 8667524 | `pages/Color.md` |
| Typography | 8667525 | `pages/Typography.md` |
| Spacing | 8667526 | `pages/Spacing.md` |
| Tokens | 8667527 | `pages/Tokens.md` |
| Foundations | 8667528 | `pages/Foundations.md` |
| Button | 8667529 | `pages/Button.md` |
| Components | 8667530 | `pages/Components.md` |
| Error handling | 8667531 | `pages/Error_handling.md` |
| Confirmation success | 8667532 | `pages/Confirmation_success.md` |
| Empty states | 8667533 | `pages/Empty_states.md` |
| Patterns | 8667534 | `pages/Patterns.md` |
| Accessibility standards | 8667535 | `pages/Accessibility_standards.md` |
| Designing for accessibility | 8667536 | `pages/Designing_for_accessibility.md` |
| Testing accessibility | 8667537 | `pages/Testing_accessibility.md` |
| Accessibility | 8667538 | `pages/Accessibility.md` |
| Voice and tone | 8667539 | `pages/Voice_and_tone.md` |
| Writing for UI | 8667540 | `pages/Writing_for_UI.md` |
| Error messages | 8667541 | `pages/Error_messages.md` |
| Content | 8667542 | `pages/Content.md` |
| Design | 8667543 | `pages/Design.md` |
| Code | 8667544 | `pages/Code.md` |
| Release notes | 8667545 | `pages/Release_notes.md` |
| Resources | 8667546 | `pages/Resources.md` |

---

## Orden de trabajo recomendado

**Prioridad alta** (fundamentos visuales — mayor impacto en la primera impresión):
1. Welcome
2. Color
3. Typography
4. Button
5. Tokens

**Prioridad media** (fundamentos y patrones):
6. Principles
7. Getting started
8. Spacing
9. Foundations
10. Components

**Accesibilidad y contenido**:
11. Accessibility (overview)
12. Accessibility standards
13. Voice and tone
14. Writing for UI
15. Error messages

**Resto**:
16. Las demás páginas en cualquier orden

---

## Notas sobre el formato en Zeroheight

- Los bloques de código `` ```css `` y `` ```jsx `` se renderizan con syntax highlighting
- Las tablas de markdown se renderizan como tablas formateadas
- Los headings `##` y `###` aparecen en la tabla de contenidos lateral de Zeroheight
- Los bloques `>` (blockquote) se renderizan como callouts destacados

---

## Fuente de verdad

El contenido de este paquete se generó a partir de:
- `/frontend/ds/README.md` — visual foundations, iconografía
- `/frontend/ds/colors_and_type.css` — todos los valores de tokens
- `/frontend/ds/tokens.md` — arquitectura de tokens
- `/frontend/ds/ACCESSIBILITY.md` — normas WCAG 2.1 AA

Si los tokens cambian en `colors_and_type.css`, actualizar también `tokens.dtcg.json` y las tablas de los archivos de página correspondientes.
