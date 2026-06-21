# Resources

Índice de recursos del Design System de Alexandria Magazine — dónde vive cada cosa y cómo acceder.

---

## Código fuente

| Recurso | Ubicación | Descripción |
|---|---|---|
| **Tokens CSS** | `/frontend/ds/colors_and_type.css` | FUENTE ÚNICA DE VERDAD — todos los custom properties |
| **Arquitectura de tokens** | `/frontend/ds/tokens.md` | Documentación de los tres niveles de tokens |
| **WCAG 2.1 AA** | `/frontend/ds/ACCESSIBILITY.md` | Normas vinculantes de accesibilidad |
| **Contexto del sistema** | `/frontend/ds/README.md` | Visual foundations, iconografía, índice |
| **Logomark** | `/frontend/ds/assets/logomark.svg` | Monograma "A" en tile azul |
| **Wordmark** | `/frontend/ds/assets/wordmark.svg` | Mark + "Alexandria" + "MAGAZINE" |

---

## Preview de componentes

Los specimens visuales están en `/frontend/ds/preview/` — archivos HTML con exemplos interactivos de cada componente y fundamento.

| Archivo | Contenido |
|---|---|
| `colors-brand.html` | Ramp de Alexandria Blue |
| `colors-neutrals.html` | Cloud ramp SLDS |
| `colors-agents.html` | Paleta de 5 agentes |
| `colors-semantic.html` | Tokens semánticos de estado |
| `type-ui.html` | Escala y uso en Studio UI |
| `type-prose.html` | Content System .prose |
| `type-mono.html` | JetBrains Mono |
| `comp-buttons.html` | 4 variantes + estados + tamaños |
| `comp-badges.html` | Badges de estado editorial |
| `comp-inputs.html` | Fields con labels, error, disabled |
| `comp-alerts.html` | Alertas de success/warning/error/info |
| `comp-toast.html` | Toasts de notificación |
| `comp-avatar.html` | Avatares con iniciales y foto |
| `comp-article-card.html` | Card de artículo científico |
| `comp-agent-node.html` | Nodo del Flow Designer |
| `spacing-scale.html` | Escala de espaciado 4px |
| `elevation.html` | Sistema de sombras |
| `radius.html` | Escala de radius |
| `icon-library.html` | Iconos Lucide del sistema |
| `a11y-contrast.html` | Verificación de contraste |
| `theme-light-dark.html` | Comparación light vs dark |
| `dataviz-charts.html` | Paleta y charts de dataviz |
| `content-callouts.html` | Callouts de artículo |

---

## Paquete Zeroheight

El paquete de contenido para el styleguide está en `/frontend/ds/zeroheight/`:

| Archivo | Descripción |
|---|---|
| `tokens.dtcg.json` | Tokens en formato W3C DTCG para importar en Figma/Tokens Studio |
| `upload_tokens.sh` | Script para cargar tokens via API de Zeroheight |
| `README.md` | Instrucciones de uso del paquete |
| `pages/*.md` | Contenido markdown por página del styleguide |

---

## Cómo contribuir al sistema

1. **Tokens:** editar solo `colors_and_type.css` — es la fuente de verdad. Los cambios se propagan a todos los componentes.
2. **Preview:** añadir specimens HTML en `preview/` para nuevos componentes.
3. **Documentación:** actualizar `tokens.md` y `ACCESSIBILITY.md` si cambias la semántica de tokens.
4. **Versioning:** documentar cambios en `zeroheight/pages/Release_notes.md`.

---

## Dependencias del sistema

```json
{
  "lucide-react": "^0.544.0",
  "@xyflow/react": "latest"
}
```

Las tipografías son open-source y se cargan desde Google Fonts — no requieren instalación local para producción:

```
Source Serif 4 — google.com/fonts (OFL)
Source Sans 3  — google.com/fonts (OFL)
JetBrains Mono — google.com/fonts (OFL)
```

---

## Referencias externas

| Recurso | URL | Para qué |
|---|---|---|
| SLDS2 Reference | lightningdesignsystem.com | Patrones y tokens SLDS |
| SLDS GitHub | github.com/salesforce-ux/design-system | Tokens YAML fuente |
| Lucide Icons | lucide.dev | Catálogo completo de iconos |
| WCAG 2.1 | w3.org/TR/WCAG21 | Criterios de accesibilidad |
| W3C DTCG | tr.designtokens.org | Especificación de formato de tokens |
| Google Fonts | fonts.google.com | Descarga y licencias OFL |
