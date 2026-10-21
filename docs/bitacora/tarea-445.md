# Tarea #445 — T20.13 Despliegue gradual, retención de informes y allowlist de egress

## 2026-10-21 — Éxito ✅

- **Rama:** `feat/t20-13-retencion-egress-despliegue`
- **PR:** la de esta rama → `develop` (`Closes #445`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC16 y §7 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.6 (#438, ya en `develop`)

### Dónde estaba el problema

T20.6 dejó la tabla de informes sin política de retención (lo anotó honestamente en la política de datos),
la compuerta no podía alcanzar Crossref/OpenAlex en un despliegue con `EGRESS_ALLOWED_DOMAINS` definida
(todo habría quedado `not_verified`), el modo de despliegue gradual solo existía como variable y no había
métricas ni correo de contacto para esos servicios.

### Qué se hizo y por qué

- **Retención** (`platform/retention.py`, `RETENTION_GATE_REPORTS_DAYS`, 90 por defecto): caducan los
  informes **de artículos no publicados**; los de un artículo `published` se conservan porque son la
  evidencia de por qué se aprobó. Con la ventana a `0` se desactiva, y la simulación (`--apply` ausente)
  no borra nada. `docs/governance/data-retention.md` pasa la tabla de «no caduca» a «caduca» y deja de
  decir que no estaba implementado; ambos `config.yaml` ganan `gate_reports_days`.
- **Egress** (`platform/egress.py`): con allowlist definida, `api.crossref.org` y `api.openalex.org` se
  añaden **solo cuando el llamador es la compuerta** (`quien="publication_gate"`). La herramienta
  `fetch_url` del modelo no gana esos hosts por el hecho de que la compuerta los necesite. Los bloqueos
  por IP interna y por redirección no cambian.
- **Despliegue gradual:** `PUBLICATION_GATE_ENFORCE` y `PUBLICATION_ALLOW_SELF_APPROVAL` pasan también por
  `config.yaml` (`publication:`), con el mismo orden de precedencia (env > yaml > defecto); la segunda
  sigue apagándose con `DEBUG=false`. Nuevo `PUBLICATION_GATE_CONTACT_EMAIL`, que viaja en el
  `User-Agent` hacia Crossref/OpenAlex (su *polite pool*) y vive en configuración, no en el repositorio.
- **Privacidad:** un test comprueba que, con un manuscrito marcado, ningún valor del texto aparece en
  URL, parámetros ni cabeceras hacia los dos servicios; solo salen DOI o título y autores de referencias.
  La política de datos lo documenta.
- **Observabilidad** (§7, cierra parte de CHK037): contadores Prometheus de baja cardinalidad
  `publication_gate_criterion_total{criterion,status}`, `publication_gate_reference_total{outcome}`
  (`cache_hit`, `resolved`, `mismatch`, `not_verified`) y `publication_gate_external_errors_total{provider,reason}`
  (incluye 429), más un log estructurado por criterio.

### Definition of Done

- [x] **AC16** — modo aviso (ya en T20.9/T20.10) configurable por YAML o entorno; metadatos de
  referencias únicamente y por `safe_get`; hosts de la compuerta añadidos a la allowlist.
- [x] Retención con política documentada y test que la compara con el código.
- [x] Tests: `backend/tests/test_gate_deployment.py` (14) y `test_data_retention.py` en verde. Suite: 1351
  pasados, los mismos 4 fallos que `develop`.
- [ ] Revisar las condiciones de uso de Crossref y OpenAlex antes de enviar títulos de trabajos inéditos
  (FW §20.7): es una comprobación legal, no de código.

### Verificación

SQLite y un `fetch` simulado; las métricas se leen del registro de Prometheus en proceso. No se ha salido
a la red.

### Fuera de alcance / notas

- Las métricas son por proceso (como el resto): con varios workers hace falta `PROMETHEUS_MULTIPROC_DIR`.
- No hay panel ni alerta sobre la tasa de `not_verified`; los contadores lo permiten.
- Sigue abierto el nombre exacto de las métricas frente a las del resto del proyecto (CHK037): se han
  usado los prefijos y etiquetas del módulo de métricas existente.
