# Tarea #435 — T20.3 Resolución de existencia contra Crossref/OpenAlex con falla cerrada (V09 nivel 2)

## 2026-10-21 — Éxito ✅ (con una medición pendiente, ver abajo)

- **Rama:** `feat/t20-3-resolucion-referencias`
- **PR:** la de esta rama → `develop` (`Closes #435`)
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC3 y AC4 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md) · épica E20 (#432)
- **Dependencias:** T20.2 (#434, ya en `develop`)

### Dónde estaba el problema

Nada comprobaba que una referencia existiera: las fuentes salían de documentos subidos al RAG sin
identificador y el texto final podía citar trabajos inventados (matriz de la Fase 0, V09).

### Qué se hizo y por qué

`backend/app/platform/publication_gate/reference_resolver.py` (nuevo), sin LLM:

- **Resolución:** con DOI, Crossref y, si no aparece, OpenAlex; sin DOI, búsqueda por título y
  autores en ambos. Un DOI que ninguno de los dos conoce es `failed` (referencia inventada).
- **Coincidencia (AC3):** título con similitud ≥ 0,90; primer autor (debe ser también el primero
  que aparece) y al menos la mitad de los demás (con «et al.» solo se exige el primero); año exacto,
  o ±1 solo si el registro es un preprint; revista tras normalizar abreviaturas («Proc. Natl. Acad.
  Sci.» ~ «Proceedings of the National Academy of Sciences»). Una discrepancia es `failed`.
- **Falla cerrada (AC4):** red caída, tiempo agotado, 429/5xx, JSON inválido, sin candidatos o
  varios igualmente plausibles → `not_verified`, que **bloquea**. Si un proveedor no responde y el
  otro no conoce el DOI, no se afirma que no exista. Valores iniciales: 10 s por consulta, 2
  reintentos con espera exponencial, 120 s por evaluación.
- **Caché** solo de positivos, 30 días (`PositiveCache`): un fallo no se cachea.
- **Enriquecimiento:** una fuente que pasa vuelve con DOI, año, revista y autores completados desde
  el registro canónico, sin pisar lo que ya traía (así AC2 se evalúa después de AC3).
- **Egress:** todo sale por `safe_get` (SPEC-024), con `User-Agent` identificable; solo viajan
  metadatos de la referencia, nunca el texto del manuscrito.
- Todos los parámetros están en `ResolverConfig`; conectarlos a `gate.references` de
  `template.yaml` es T20.4 (#436).

### Definition of Done

- [x] **AC3** y **AC4** — cubiertos con un `fetch` simulado: `backend/tests/test_gate_reference_existence.py` (32 tests).
- [x] Suite completa: 1158 pasados; los mismos 4 fallos que `develop`.
- [ ] **Objetivo medible de AC3 (≥ 90 % de referencias reales con DOI se resuelven y pasan):** el test
  usa registros **simulados** de 10 trabajos reales, así que prueba la lógica de coincidencia, **no**
  la tasa real contra Crossref. Esa medición con la red queda pendiente (necesita salida a internet y
  un conjunto de prueba revisado).

### Verificación

Ningún test sale a la red. No se ha ejecutado el resolutor contra Crossref/OpenAlex reales.

### Fuera de alcance / notas

- Los hosts `api.crossref.org` y `api.openalex.org` se añaden a `EGRESS_ALLOWED_DOMAINS` en T20.13 (AC16);
  hasta entonces, con esa lista definida, la resolución sería `not_verified`.
- La caché es en memoria por proceso: se pierde al reiniciar. Una caché persistente queda como mejora.
- Abiertos del checklist: fuentes sin DOI que no indexan (CHK004), «et al.» parcial (CHK016) y alias de
  revista (CHK017, aquí resuelto con una regla de abreviatura, no con un diccionario).
