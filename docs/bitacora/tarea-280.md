# Tarea #280 — bug: el preset ACL era inalcanzable desde la UI

## 2026-08-17 08:25 — Completada ✅

- **Rama:** `fix/paper-acl-format-enum`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #280`)
- **Spec/ADR:** SPEC-022, Épica E11. Regresión introducida entre **T11.1 (#247)** y
  **T11.4 (#250)**.
- **Origen:** detectado al revisar el backlog, no reportado por el usuario.

### Qué pasaba

El panel de diseño ofrecía «ACL — conferencia (2 columnas)» y al elegirlo la previa
no se actualizaba: `POST /articles/{id}/preview` respondía **422**.
`PaperPreviewDTO.scientific_format` está tipado como `ScientificFormat`, y el enum
no tenía el valor `acl` — la plantilla existía en `paper_layout._FORMAT_STYLE`
desde T11.1, pero **no había ningún valor de enum que la alcanzara**.

### Qué se hizo

- **`models/enums.py`**: `ACL = "acl"` en `ScientificFormat`. Es el arreglo del 422.
- **`core/database.py`**: falta `ALTER TYPE scientificformat ADD VALUE 'acl'` junto
  a los de `chicago` y `nature`. Sin ella, en Postgres el enum nativo rechazaría el
  valor aunque Pydantic lo aceptase.
- **`adapters/formateador.py`**: rama `acl` en `format_source_deterministic`.
  Caía al `else` numerado, así que el paper habría salido con citas en texto
  autor-año — `(Autor et al., Año)`, que es lo que dice su propia
  `_FORMAT_INSTRUCTIONS["acl"]` — y una bibliografía `[1]`, `[2]`. Ahora es
  autor-año sin numerar, estilo ACL Anthology.
- **`AgentEditorModal.jsx`**: ACL seleccionable también en el perfil del agente,
  no solo en el panel de diseño.
- **Docs de agente**: `publicador.agent.md` y `formateador.agent.md` listaban
  formatos desactualizados (el formateador seguía diciendo «`apa`, `ieee`,
  `vancouver`», sin `chicago`, `nature` ni `acl`).

### Por qué no lo cogieron los tests de T11.1

`test_paper_layout_acl.py` llama a `build_paper_html(scientific_format="acl")`
**directamente**, saltándose la capa que rechazaba el valor. La plantilla estaba
probada; su *alcanzabilidad*, no. Es el patrón de error a recordar: probar el
componente sin probar que algo pueda llegar a él.

### Decisiones documentadas

- **Se añade una invariante, no solo el caso**: `test_every_layout_preset_is_selectable`
  comprueba que **todo** preset de `_FORMAT_STYLE` tenga un valor de enum, y
  `test_every_layout_preset_has_formateador_guidance` que tenga etiqueta e
  instrucción de cita. Arreglar solo `acl` habría dejado el siguiente preset
  expuesto al mismo olvido.
- **La bibliografía sigue a la cita en texto, no al revés**: hay un test que fija
  que `_FORMAT_INSTRUCTIONS["acl"]` es autor-año, para que un cambio a numerada
  arrastre también la rama de bibliografía.
- **No se toca `_authors_block`**: reventaba con `AttributeError` al recibir
  autores como cadenas en lugar de dicts (lo descubrí escribiendo el test). El DTO
  garantiza `AuthorDTO`, así que no es alcanzable por API; queda fuera de alcance
  para no mezclar arreglos.

### Test nuevo

`backend/tests/test_paper_acl_format_reachable.py` (12 casos): el enum acepta
`acl`; **toda** plantilla de `_FORMAT_STYLE` es seleccionable y tiene guía de
citas; el DTO de preview acepta `acl` y sigue rechazando `mla`; la bibliografía
ACL es autor-año con `In <journal>.` y enlace, omite campos ausentes sin «N/A», y
los estilos numerados (`ieee`, `vancouver`, `nature`) siguen numerados; el paper
ACL sigue saliendo a 2 columnas.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_paper_acl_format_reachable.py -q
# → 12 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 257 passed
npm run build && npm run build:public   # ambos OK
```

### Definition of Done

- [x] El 422 desaparece: ACL seleccionable en el panel de diseño y en el perfil
  del agente, y la maqueta sale a 2 columnas.
- [x] Test que falla sin el arreglo + invariante que impide la reincidencia.
- [x] Docs de agente actualizadas.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `fix/` hacia `develop`.

### Seguimiento

El punto de Postgres es un ejemplo concreto de la deuda de **#168 (T4.1)**: los 15
`ALTER` ad-hoc de `core/database.py` corren dentro de un `try/except: pass` que se
traga cualquier fallo, y por eso una omisión así no da la cara. Se aborda en #168,
que es la siguiente tarea.
