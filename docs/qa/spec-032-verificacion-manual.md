# SPEC-032 — guía de verificación manual

- **Para qué:** lo que los tests no pueden probar —la interfaz en un navegador y el comportamiento con un LLM real—. Está pensada para quien haga QA (Pantoja / Molina) y para cerrar los criterios de SPEC-032 que siguen sin verificar de verdad.
- **Tiempo estimado:** ~1 hora si hay un LLM disponible.
- **Resultado:** al terminar, apunta en cada fila ✅ / ❌ y qué viste; los ❌ van a un issue con captura.

## 0. Preparación

```bash
# Backend (desde backend/): modo aviso al principio, para ver lo que pasaría sin bloquear
DEBUG=true SECRET_KEY=qa-local PUBLICATION_GATE_ENFORCE=false uvicorn app.main:app --reload --port 8000
cd frontend && npm run dev          # http://localhost:5173
```

- Necesitas **tres usuarios**: una persona *autora* (redactor), otra *revisora asignada* y un *admin*. La que lanza el pipeline no puede aprobar su propio artículo.
- Un LLM configurado (`LLM_PROVIDER`) y, para las referencias, salida a internet (Crossref/OpenAlex) o el `fetch` simulado.
- Para desarrollo de un solo usuario existe `PUBLICATION_ALLOW_SELF_APPROVAL=true` (solo con `DEBUG`).
- Opcional: `PUBLICATION_GATE_CONTACT_EMAIL=tu@correo.org`.

## 1. Recorrido principal (AC5, AC6, AC8)

| # | Paso | Esperado | Resultado |
|---|---|---|---|
| 1.1 | Como autora, ejecutar el pipeline completo (investigador → publicador) con documentos **con DOI** en el RAG | El artículo termina en **«Pendiente»** (`in_review`), **nunca «Publicado»** | |
| 1.2 | Abrir el artículo | El panel **Compuerta de publicación** muestra los cuatro criterios y la lista «N criterios aún sin comprobar (no bloquean)» con sus fases | |
| 1.3 | Sin declarar autor responsable: la revisora pulsa **Aprobar** | Mensaje «Declara un autor responsable antes de aprobar» (409 `no_responsible_author`) | |
| 1.4 | La autora pulsa **Declararme autor responsable** | La tarjeta pasa a «Declarado (tú)» | |
| 1.5 | La **autora** intenta aprobar (si es también revisora) | Rechazado: «Quien lanzó el pipeline no puede aprobar su propio artículo» | |
| 1.6 | Asignar la revisora; la revisora pulsa **Aprobar** | Pasa a **«Publicado»**; aparece en la revista pública | |
| 1.7 | Editar el texto de un artículo `in_review` y volver a pulsar Aprobar | «El texto cambió desde la última evaluación…»; el panel avisa de que el informe es de otro texto | |
| 1.8 | Pulsar **Reevaluar** | Se crea un informe nuevo y vuelve a poder aprobarse | |

## 2. Bloqueantes de la compuerta (AC1, AC2, AC11, AC14)

| # | Paso | Esperado | Resultado |
|---|---|---|---|
| 2.1 | Ejecutar con `PUBLICATION_GATE_ENFORCE=true` y un texto que contenga `TODO` o `(Author, Year)` | El artículo vuelve a **Borrador**; el aviso de la ejecución dice «La compuerta bloquea la publicación» y nombra el criterio y **el agente al que corresponde** (Redactor) | |
| 2.2 | Un texto sin secciones IMRaD o con «Resultados y Discusión» en un solo encabezado | Criterio de estructura falla, nombra la sección | |
| 2.3 | Un documento del RAG **sin DOI** | Referencias `No verificado` (bloquea); el informe dice el motivo | |
| 2.4 | Cortar internet y ejecutar | Referencias `No verificado` (falla cerrada), **no** se aprueba | |
| 2.5 | Citar `(Author, Year)` **entre comillas de código** en el texto | No cuenta como marcador | |

## 3. Revisor y vueltas (AC7, AC15)

| # | Paso | Esperado | Resultado |
|---|---|---|---|
| 3.1 | Con el LLM del Revisor apagado o devolviendo basura | La revisión es `no verificada`: **no** aparece una puntuación inventada (85) ni comentarios simulados | |
| 3.2 | Un borrador que el Revisor rechace 3 veces | La ejecución **se detiene**: no se formatea ni se publica; el artículo pasa a **«Requiere revisión humana»** con puntuación y comentarios; aviso en la ejecución | |
| 3.3 | Reanudar (`resume`) esa ejecución | El estado no cambia y el contador no se reinicia | |
| 3.4 | Volver a ejecutar el pipeline | Vuelve a **Borrador**, con los comentarios aún visibles | |
| 3.5 | La revisora pulsa **Rechazar** desde «Requiere revisión humana» | Pasa a **Rechazado** (antes daba 422) | |

## 4. Una sola puerta (AC10, AC13)

| # | Paso | Esperado | Resultado |
|---|---|---|---|
| 4.1 | Como admin no propietario, **Publicar borrador** sobre un borrador sin compuerta | Se evalúa la compuerta y, si hay bloqueantes o no hubo revisión, **no publica** (mensaje con el motivo) | |
| 4.2 | Un artículo escrito a mano (sin pipeline) | No se publica: «El texto no ha pasado por una revisión» (`review_missing`) | |

## 5. Interfaz (T20.14) — lo que no se ha visto nunca en un navegador

- [ ] El panel de la compuerta **cabe** en la barra lateral de 280 px: sin texto cortado ni desbordes, también con 5+ líneas de evidencia.
- [ ] Tema **claro y oscuro**: los distintivos (Superado / No supera / No verificado / Pendiente de fase) se leen bien.
- [ ] Móvil (≈ 375 px): la barra lateral baja bajo el artículo sin romper la rejilla.
- [ ] El aviso de la ejecución (bloqueantes / revisión humana) es visible sin desplazarse y no tapa el log.
- [ ] La pestaña **«Revisión humana»** del listado filtra y el distintivo se entiende.
- [ ] Teclado: el botón **Reevaluar**, **Reintentar** y **Declararme autor responsable** son alcanzables y tienen nombre accesible.
- [ ] Si el informe no carga (apaga el backend un momento), el panel muestra el error con **Reintentar** en vez de quedarse cargando.

## 6. Despliegue y operación

- [ ] `GET /metrics` expone `publication_gate_criterion_total`, `publication_gate_reference_total` y `publication_gate_external_errors_total` tras una ejecución.
- [ ] Con `EGRESS_ALLOWED_DOMAINS=otro.org`, la compuerta **sigue** alcanzando Crossref/OpenAlex y la herramienta `fetch_url` del modelo **no** (probar `fetch_url` a `https://api.crossref.org/`).
- [ ] `python -m app.platform.retention` (simulación) lista `gate_reports`; un informe de un artículo publicado no aparece como caducable.
- [ ] En Postgres: `alembic upgrade head`, `alembic check` y el enum `articlestatus` contiene `REQUIRES_HUMAN_REVIEW` (lo comprueba el job de CI `migrations-postgres`).

## 7. Verificaciones que ya estaban pendientes de las correcciones anteriores

Del plan de hallazgos de AlejandrIA Magazine (bitácoras [410](../bitacora/tarea-410.md)–[414](../bitacora/tarea-414.md)), sin validar aún en navegador por QA:

- [ ] **BUG-003** — flujo de extremo a extremo con el diseñador de flujos (ver la bitácora para el caso exacto).
- [ ] **BUG-005** — causa raíz marcada como **hipótesis**: confirmar o descartar.
- [ ] **UX-002** — comprobación visual.

## 8. Medición con la red de AC3

```bash
cd backend
DEBUG=true SECRET_KEY=qa-local python ../scripts/measure_reference_resolution.py --contact tu@correo.org
```

Resultado de referencia (2026-10-21): 18/20 con DOI (90 %), 10/12 sin DOI, 6/6 controles negativos bloqueados. Repetirla con un conjunto **de la revista real** —preprints, español, informes técnicos— y anotar el resultado en [`medicion-ac3-spec-032.md`](../reports/medicion-ac3-spec-032.md).
