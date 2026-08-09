# SPEC-022: Maquetación editable del paper y personalización antes de publicar

- **Estado:** Ready
- **Autor:** Equipo de plataforma
- **Fecha:** 2026-07-04
- **Épica:** E11 (Publicación y maquetación editable)
- **ADR relacionado:** — (posible ADR nuevo sobre "personalizar parametrizando el preset, no editando el HTML final")
- **Severidad:** 🟡

> **Ready** (pipeline ADR-0007): ambigüedades **resueltas** con `/speckit-clarify`
> (ver `## Clarifications`, sesión 2026-07-04). `/speckit-checklist` queda como
> mejora opcional (no bloqueante). Al estar Ready, `/sdd-sync` siembra su épica E11 y tareas.

## 1. Problema

La maquetación del paper la genera de forma **determinista** `paper_layout.py`
(`build_paper_html`) como HTML+CSS autocontenido, a partir de un **preset fijo**
por formato de citación (`apa`, `ieee`, `vancouver`, `chicago`, `nature`). El
usuario **no puede** ajustar la presentación (fuente, color, nº de columnas) ni
insertar imágenes; la `PaperViewPage` es **solo lectura** (`<iframe srcdoc>` +
Imprimir). La edición de contenido existe **parcialmente**: `ArticleDetailPage`
permite editar cuerpo/autores/abstract (`updateArticle`) pero no la presentación
ni con vista previa de la maqueta final. Falta además un preset de **conferencia
a 2 columnas** (estilo ACL) frecuente en publicaciones científicas.

## 2. Objetivos / No-objetivos

- **Objetivos:** (a) preset de maquetación **conferencia (2 columnas)**;
  (b) **panel de personalización** en pantalla (fuente, color de acento, nº de
  columnas) con **vista previa en vivo**; (c) **edición de texto** (cuerpo,
  autores, abstract) integrada con la previa; (d) **imágenes/figuras** subibles
  e insertables; (e) el tema se **persiste por artículo**.
- **No-objetivos:** editor **WYSIWYG** que edite el HTML maquetado directamente
  (choca con la generación determinista y con el `sandbox` de T2.2); diseño
  libre de plantillas sin restricciones; edición colaborativa en tiempo real.

## Clarifications

### Session 2026-07-04

- Q: ¿Cómo se renderiza la vista previa del paper (AC3)? → A: **Server-side** — endpoint que reutiliza `paper_layout.py`; el frontend hace *debounce* y repinta el `<iframe>`. Única fuente de verdad; previa == PDF.
- Q: ¿Dónde se almacenan las imágenes/figuras (AC5)? → A: **Store de assets por proyecto** — almacén de objetos con `project_id`, separado del RAG (Qdrant es solo para embeddings); respeta el aislamiento por tenant (E8).
- Q: ¿De dónde salen los valores por defecto del tema (AC2)? → A: **Hereda del proyecto/tenant** — cada proyecto define un tema por defecto; el artículo lo hereda y puede sobreescribirlo (cadena: proyecto → artículo, con el preset del formato como base).
- Q: ¿Qué tipo de allowlist de fuentes (AC2)? → A: **Curada web-safe** — lista fija de familias del sistema (serif: Times/Georgia; sans: Helvetica/Arial; +alguna más), sin embeber webfonts; renderiza igual al imprimir a PDF. Ampliable después.
- Q: ¿Cómo se elige el color de acento (AC2)? → A: **Paleta de tokens (E7)** — set curado del design system (no color libre); coherencia visual, identidad por tenant y menor superficie de saneo.

## 3. Criterios de aceptación

- [ ] **AC1** — *Given* `scientific_format = "acl"`, *When* se genera el paper
  con `build_paper_html`, *Then* el HTML resultante es a **2 columnas** con
  serif, texto **justificado**, **secciones numeradas** (contadores CSS) y
  **referencias con sangría francesa**; verificable por test sobre marcadores
  estructurales/CSS del HTML (sin navegador).
- [ ] **AC2** — *Given* un tema `{font, accent_color, columns}` asociado al
  artículo, *When* se genera la maqueta, *Then* esos valores **sobreescriben**
  los del preset y quedan **persistidos con el artículo**; un valor no permitido
  (fuera de la **allowlist curada de fuentes web-safe** o color fuera de la **paleta de tokens del design system**) **cae al valor por
  defecto** sin romper la maqueta. Los defaults del tema se **heredan del
  proyecto/tenant** (cadena de resolución: preset del formato → tema del
  proyecto → tema del artículo).
- [ ] **AC3** — *Given* la pantalla de edición de un artículo en borrador,
  *When* el usuario cambia texto o cualquier control del tema, *Then* la **vista
  previa se re-renderiza** mostrando el cambio **sin publicar**, en ≤ 1 s tras
  el último cambio (debounce). La previa se genera **server-side** en un
  endpoint que reutiliza `paper_layout.py` (única fuente de verdad: previa == PDF).
- [ ] **AC4** — *Given* un artículo en borrador, *When* el usuario edita
  cuerpo/autores/abstract y guarda, *Then* `updateArticle` persiste los cambios
  y **la publicación usa la versión editada** (extiende el flujo actual de
  `ArticleDetailPage`).
- [ ] **AC5** — *Given* una subida de imagen, *When* su contenido real (magic
  bytes) **no** corresponde a un tipo permitido, *Then* se **rechaza con `400`**
  (reutiliza la validación de T2.3, #161); *When* es válida, *Then* se
  **almacena** en un **store de assets por proyecto** (con `project_id`, separado
  del RAG), puede **insertarse** en el cuerpo (`![alt](ref)`) y **aparece** en la
  maqueta generada y en el PDF.
- [ ] **AC6** — Existen **tests** que cubren AC1–AC5: layout determinista
  (AC1/AC2), validación de tema (AC2), preview (AC3), publicación con edición
  (AC4) y rechazo/aceptación de imágenes (AC5).

## 4. Diseño propuesto

- **Preset ACL** (AC1): nuevo `"acl"` en `_FORMAT_STYLE` de
  `backend/app/modules/agents/adapters/paper_layout.py` (columns=2, Times serif,
  ~10pt) + CSS de numeración por contadores, superíndices de afiliación y
  sangría francesa. Base ya prototipada.
- **Tema parametrizado** (AC2): `build_paper_html` acepta un `theme` opcional
  (`font`, `accent_color`, `columns`) con **allowlist** y saneo; se guarda en el
  artículo (`article.theme` JSON). Resolución en cascada: **preset del formato → tema del proyecto → tema del artículo** (el más específico gana). Nada de CSS libre del usuario (evita inyección).
- **Preview server-side** (AC3): endpoint `POST /articles/{id}/preview` que toma
  `body + metadata + theme` (sin persistir) y devuelve el HTML de `paper_layout`
  para el `<iframe srcdoc>`; el frontend hace *debounce* y repinta. Única fuente
  de verdad de la maqueta = `paper_layout.py`.
- **Panel de personalización** (AC3/AC4): en `ArticleDetailPage` (o vista nueva),
  controles de fuente (allowlist web-safe), acento (paleta de tokens E7) y columnas + edición de texto ya
  existente, con la previa al lado. Publicar usa lo editado.
- **Imágenes** (AC5): subida validada por *magic bytes* (T2.3/#161), almacenada
  en un **store de assets por proyecto** (separado del RAG) y referenciable; el conversor markdown de `paper_layout` añade soporte de
  `![alt](ref)` y estilo de figura/caption (ya prototipado a doble columna).

## 5. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| CSS/HTML libre del usuario → XSS en la maqueta | Alto | El usuario **no** escribe CSS: solo elige valores de una allowlist; el iframe mantiene `sandbox` (T2.2) |
| Preview server-side por cada tecla → carga | Medio | Debounce ≥ 400 ms; render determinista y barato (sin LLM) |
| Imágenes maliciosas | Medio | Validación por *magic bytes* (T2.3) + tipos permitidos |
| Divergencia previa ↔ PDF final | Medio | Misma función `paper_layout` para previa y publicación |

## 6. Plan de pruebas

Unit del preset ACL y del saneo de tema (allowlist, fallback) sobre el HTML
generado (determinista, sin navegador); unit del endpoint de preview
(body+theme → HTML esperado); integración de `updateArticle` + publicación con
contenido editado; validación de subida de imágenes (válida/rechazada).

## 7. Impacto operativo / observabilidad

Nuevo campo `theme` en el artículo (migración Alembic, T4.1); almacenamiento de
imágenes documentado; sin dependencias nuevas de maquetado (sigue siendo
HTML+CSS + impresión del navegador).

## 8. Backlog (sincronización SDD)

```yaml
# sdd-sync v1
epic:
  id: E11
  title: "Publicación y maquetación editable"
  area: area/ux
tasks:
  - id: T11.1
    title: "Preset de maquetación conferencia (ACL, 2 columnas) en paper_layout"
    sev: medium
    depends_on: []
    acceptance: [AC1]
  - id: T11.2
    title: "Tema editable (fuente/color/columnas) parametrizando el preset + persistencia por artículo"
    sev: medium
    depends_on: [T11.1]
    acceptance: [AC2]
  - id: T11.3
    title: "Endpoint de vista previa server-side (body+tema -> HTML)"
    sev: medium
    depends_on: [T11.2]
    acceptance: [AC3]
  - id: T11.4
    title: "Panel de personalización en la UI con vista previa en vivo y edición de texto"
    sev: high
    depends_on: [T11.3]
    acceptance: [AC3, AC4]
  - id: T11.5
    title: "Imágenes/figuras: subida validada (magic bytes) + insercion + render en la maqueta"
    sev: medium
    depends_on: [T11.4, "#161"]
    acceptance: [AC5]
```
