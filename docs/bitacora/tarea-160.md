# Tarea #160 — T2.2 Sanear URLs javascript:/data: en paper_layout + sandbox en iframe

## 2026-08-16 18:34 — Completada ✅

- **Rama:** `sec/160-sanitize-urls-sandbox`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #160`)
- **Spec/ADR:** SPEC-016 (AppSec), Épica E2. Criterio vinculante: **AC1** (+ AC4).
- **Dependencias:** Ninguna.

### Qué se hizo

Las dos mitades del AC1.

**1. Saneo de enlaces en `paper_layout`.** El conversor markdown emitía el `href`
**tal cual**: `[texto](javascript:alert(1))` se convertía en un ancla viva. Como
la maqueta se renderiza en un iframe y se imprime, eso era un vector de **XSS
almacenado contra todo lector** del artículo publicado.

- `_safe_href()` con allowlist de esquemas: `http://`, `https://`, `mailto:` y
  enlaces relativos/ancla (que no llevan esquema). Todo lo demás se descarta.
- **Normaliza antes de comparar**: elimina caracteres de control y espacios
  (`\x00-\x20`), porque los navegadores interpretan `  javascript:` y
  `java\tscript:` como el mismo esquema.
- Un enlace rechazado **conserva su texto** y pierde el ancla: el lector sigue
  viendo las palabras.
- El `href` pasa por `html.escape(quote=True)`, así que una comilla en la URL no
  puede escaparse del atributo e inyectar otro.

**2. `sandbox` en el iframe de `PaperViewPage`** — la vista desde la que se
imprime a PDF: `sandbox="allow-same-origin allow-modals"`. **Sin
`allow-scripts`**, que es lo que exige el AC («sin `allow-same-origin` +
`allow-scripts` simultáneos»).

### Decisión: por qué esos dos flags y no `sandbox=""`

El botón Imprimir llama a `iframeRef.current.contentWindow.print()` desde el
padre. Con `sandbox=""` el documento pasa a un origen opaco y ese acceso lanza
`SecurityError`: **se rompería la impresión**, que es la función principal de la
vista. `allow-same-origin` la conserva y `allow-modals` permite el diálogo de
impresión; ninguno de los dos habilita la ejecución de scripts por sí solo, y la
pareja peligrosa nunca se combina.

*(La vista nueva de diseño, T11.4, sí usa `sandbox=""`: allí no se imprime.)*

### Test nuevo

`backend/tests/test_paper_link_sanitizing.py` (16 casos): esquemas peligrosos
descartados (`javascript:` en varias formas —mayúsculas, con espacios, con tab
intercalado—, `data:text/html`, `vbscript:`, `file:`); el texto del enlace
rechazado se conserva; enlaces legítimos intactos (https, http, mailto, ancla,
relativo); comillas que no pueden romper el atributo; y que los **DOI del
Formateador y la lista de referencias no son daño colateral**.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_paper_link_sanitizing.py -q
# → 16 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q      # → 261 passed
npm run build                                                          # OK
```

**Verificado en navegador** (Chromium sobre el stack real), que es donde se
comprueba lo que importa de un sandbox:

| Comprobación | Resultado |
|---|---|
| atributo aplicado | `allow-same-origin allow-modals` |
| el padre alcanza `contentWindow.print` | ✅ `function` — **Imprimir sigue funcionando** |
| script inyectado en el documento del paper | ✅ **no se ejecuta** |

### Nota sobre un test que falló primero

La primera versión afirmaba que la cadena «javascript» no aparecía en la salida.
Falló con `[aquí](  javascript:…)`: con espacios delante la regex de enlaces no
casa y el markdown queda como **texto literal** — sin `<a>` ni `href`, o sea
inofensivo, y **falla en cerrado**. La aserción era demasiado estricta; se
corrigió para comprobar la propiedad real de seguridad (no hay ancla ni `href`).

### Definition of Done (AC1)

- [x] **AC1** — los esquemas `javascript:`/`data:` quedan eliminados en el
  conversor, y el iframe de `PaperViewPage` lleva `sandbox` **sin**
  `allow-same-origin`+`allow-scripts` simultáneos.
- [x] Tests que cubren el cambio, en verde (16 nuevos; 261 en la suite).
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Estado de E2

Con T2.2 y T2.3 (#161) cerradas, de la épica E2 queda **T2.4 (#162)** —
manejador global de excepciones— y la decisión humana sobre **#159** (huérfana
de SPEC-002, `Superseded`).
