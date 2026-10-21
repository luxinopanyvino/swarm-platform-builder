# Tarea #436 — T20.4 Módulo de compuerta, V03 IMRaD y configuración `gate:` con validación al cargar

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-4-modulo-compuerta`
- **PR:** la de esta rama → `develop` (`Closes #436`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC5 y AC11 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.1 (#433), T20.2 (#434), T20.3 (#435), todas en `develop`

### Dónde estaba el problema

Los criterios existían sueltos (marcadores, estructura de referencias, existencia) y no había quien
los ejecutara en orden ni una forma de que un proyecto declarara qué compuerta aplica. V03 (IMRaD)
no se comprobaba en ningún sitio.

### Qué se hizo y por qué

- `publication_gate/gate.py`: `evaluate_gate(texto, fuentes, config)` ejecuta en el orden de la spec
  —resolver y enriquecer referencias, estructura de referencias, marcadores, IMRaD— y devuelve un
  `GateReport` (`criteria`, `blockers`, `passed`, `pending`, `as_dict()`). No nombra agentes.
- `publication_gate/structure.py` (V03): IMRaD por defecto con un diccionario de títulos por idioma
  («Métodos»/«Metodología»/«Methods»…). Detecta sección ausente, desordenada y **Resultados y
  Discusión fundidos** en un solo encabezado. Pasa si cumple en alguno de los idiomas declarados.
  Sin diccionario declarado es `not_verified`: no se aprueba lo que no se puede comprobar.
- `publication_gate/config.py`: `parse_gate` valida el bloque `gate:` (rangos numéricos, ajustes
  desconocidos, títulos por sección, entradas de `pending`).
- `platform/projects/loader.py`: `ProjectPackage.gate`; una compuerta mal escrita falla **al cargar**
  la plantilla con `TemplateError`, igual que `flow_rules`. Un proyecto sin `gate:` carga con `gate = None`.
- `projects/alejandria-magazine/template.yaml`: bloque `gate:` con los marcadores de AC1, los
  parámetros de `references` (AC3/AC4), la estructura IMRaD en es/en y los criterios `pending`
  (V01, V05–V08, V12–V14, V16, cada uno con la fase que lo construye, según la matriz de la Fase 0).
  Un test comprueba que la lista de marcadores de la plantilla coincide con la del módulo.

### Definition of Done

- [x] **AC5** — la compuerta compone un informe con un resultado por criterio; solo `failed` y
  `not_verified` bloquean y los pendientes se listan con su fase.
- [x] **AC11** — V03 con diccionario por idioma en `template.yaml`.
- [x] Tests: `backend/tests/test_publication_gate.py` (22). Suite: 1181 pasados, los mismos 4 fallos que `develop`.
- [ ] **Sin conectar todavía:** la compuerta no la invoca ningún agente. Persistirla y llamarla desde
  el Publicador son T20.6 (#438) y T20.9 (#441); hasta entonces el flujo no cambia.

### Verificación

Con `fetch` simulado, sin red. Los criterios `not_implemented` aparecen en `pending` y no en `criteria`:
el estado `not_implemented` por criterio dentro del informe persistido se materializa en T20.6.

### Fuera de alcance / notas

- No se interpretó «el Formateador falla» (T20.2): sigue sin lanzar excepción.
- Los idiomas y títulos de V03 son ampliables solo en el YAML.
