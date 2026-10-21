# SPEC-032 — decisiones y huecos pendientes

- **Fecha:** 2026-10-21 · **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) · **Épica:** E20 (#432)
- **Para qué sirve:** la implementación de E20 está hecha y mergeada; esto reúne **lo que queda abierto** y lo que la medición real y la implementación destaparon, cada cosa con una recomendación para que se pueda decidir rápido. No se ha decidido nada por la persona responsable: las recomendaciones son mías.
- Las marcadas **[decisión]** necesitan a una persona; las marcadas **[trabajo]** son tareas ya claras que no requieren decidir.

## A. Lo que la medición real y la implementación destaparon

| # | Tema | Recomendación | Tipo |
|---|---|---|---|
| **DEC-1** | **DOI de arXiv (DataCite).** Crossref no los conoce (404) y todo recae en OpenAlex, que falló 2 de 3 en la medición ([informe](medicion-ac3-spec-032.md)). Sin esto, los preprints de IA —el caso común— fallan o dependen de un dato de calidad irregular. | Añadir `api.datacite.org` como tercer proveedor para DOI con prefijo `10.48550`. Implica enmendar [ADR-0011](../adr/0011-publication-gate-fail-closed.md) (un host más en el camino crítico de publicar) y la allowlist de egress. Es la mejora de mayor valor para la tasa de resolución. | ✅ **Aprobado e implementado en #482:** DataCite como proveedor del prefijo `10.48550/`, ADR-0011 enmendado y egress ampliado. Medición: 20/20 con DOI. | hecho |
| **DEC-2** | **Año de los preprints.** AC3 exige año exacto (±1 solo preprint↔publicada). OpenAlex dio 2025 para un arXiv de 2017. | **Mantener estricto.** Relajarlo abre la puerta a citas con el año cambiado. Si DEC-1 se aprueba, el dato vendrá de DataCite y el problema se reduce solo. | ✅ **Se mantiene estricto** (decisión tomada). Con DataCite el dato del preprint viene del registrador y el problema desaparece sin relajar la regla. | hecho |
| **DEC-3** | **Un artículo escrito a mano no puede publicarse** (`review_missing`): no pasó por el Revisor. | Aceptarlo y documentarlo: para publicar texto propio se pasa por `revisor → formateador → publicador`, que ya es posible. La alternativa (una «revisión humana equivalente») es una regla nueva y debilita la puerta única. | decisión |
| **DEC-4** | **Cómo activar la compuerta.** Con `PUBLICATION_GATE_ENFORCE=true` casi nada pasa hoy: las fuentes del RAG no traen DOI. | Desplegar con `false` (registra y avisa), medir durante 1–2 semanas qué fracción de borradores pasaría y por qué criterio, y pasar a `true` cuando los bloqueantes sean accionables. Falta además una entrada en la interfaz para **aportar el DOI a mano** (CHK009), que es lo que más desbloquearía. | ✅ **Aprobado e implementado en #484:** `gate_enforce: false` en `config.yaml`, reporte de medición y [procedimiento](../governance/publication-gate-rollout.md). La entrada para aportar el DOI a mano llegó en #472. | hecho |
| **DEC-5** | **Código muerto `modules/articles`** (dominio hexagonal con su propio enum y un `publish()` sin compuerta). Hoy un test impide conectarlo. | ✅ **Resuelto en #478:** borrado. Un test impide que reaparezca. | hecho |
| **DEC-6** | **El Publicador se traga los errores de base de datos** (`except Exception` + log). Si falla la evaluación de la compuerta o su escritura, el pipeline sigue y el artículo queda sin cambios, **sin avisar** a la persona. No publica de más (falla del lado seguro), pero oculta el fallo. | ✅ **Resuelto en #476:** el error sube y el paso queda `failed` (CHK031). | hecho |
| **DEC-7** | **Carrera en la aprobación** (CHK030): dos aprobaciones simultáneas leen `in_review` a la vez. | ✅ **Resuelto en #476:** `approve` y `publish` bloquean la fila (`FOR UPDATE`) y, tras reevaluar, la vuelven a bloquear y recomprueban el estado (CHK030). | hecho |
| **DEC-8** | `test_la_spec_de_finetune_sigue_en_draft` falla en `develop` desde antes de E20: SPEC-031 ya no está en `Draft`. | Revisar si SPEC-031 salió de Draft con su ADR (el test lo pide) y actualizar el test o la spec. No es de E20. | ✅ **Resuelto en #480:** ADR-0012 escrito y test retirado. | hecho |

## B. Los 10 puntos abiertos del checklist de requisitos

[`SPEC-032-publication-gate.md`](../specs/checklists/SPEC-032-publication-gate.md), 33/43 antes de implementar. La implementación resolvió algunos de facto; **el checklist evalúa la spec, no el código**, así que se han añadido los hechos a la spec (sección *Clarifications*) y solo se marcan CHK034 y CHK037.

| CHK | Pregunta | Estado y recomendación |
|---|---|---|
| 004 | Fuentes que Crossref/OpenAlex no indexan (tesis, informes, webs, libros) | **Abierta [decisión].** Hoy quedan `not_verified` y bloquean. Recomendación: mantener el bloqueo y, en la Fase 4, permitir una *excepción documentada por referencia* firmada por una persona (no un bypass global). Es la tensión real del framework: V09 pide origen recuperado. |
| 015 | Qué es «autor responsable declarado» y quién lo rellena | **Implementado:** `PUT /articles/{id}/responsible-author`, lo declara el autor del artículo o un admin, debe ser un usuario activo. Falta decidir el valor por defecto: recomiendo que por defecto sea el autor del artículo, editable. |
| 016 | «Mitad de los demás autores» con listas parciales / «et al.» | **Implementado:** con «et al.» solo se exige el primer autor; sin él, la mitad de los restantes. Documentado en la spec. |
| 017 | Alias y abreviaturas de revista | **Implementado sin diccionario:** regla de abreviatura por palabra (≥ 60 % de las significativas, ignorando genéricas). Medido con Crossref. |
| 030 | Rechazo con comentario, aprobaciones concurrentes, aprobación con compuerta caducada | Rechazo y caducidad: **cubiertos** (409 `text_changed`, `reject` con comentario). Concurrencia: **resuelta** (#476, DEC-7). |
| 031 | Recuperación si falla la escritura del informe o la migración | **Resuelta** (#476, DEC-6). La migración tiene `downgrade` y ahora un job de CI en Postgres. |
| 033 | Referencia duplicada / dos documentos con el mismo DOI | **Abierta.** Hoy ambos se resuelven y pasan. Recomiendo avisar (no bloquear) en el informe. |
| 034 | Manuscrito sin ninguna referencia | **Resuelta:** `reference_existence` queda `not_verified` y bloquea. ✔ marcada. |
| 037 | Nombres de logs y métricas | **Resuelta en T20.13:** `publication_gate_criterion_total`, `publication_gate_reference_total`, `publication_gate_external_errors_total`. ✔ marcada. |
| 039 | Cobertura real de Crossref/OpenAlex sobre el corpus del proyecto | **Parcial.** La [medición](medicion-ac3-spec-032.md) cubre 20 trabajos conocidos; falta una muestra del corpus real (preprints, español, informes). |

## C. Decisiones D1–D5 del plan de mejoras

Del [plan de implementación](../bitacora/tarea-427.md) (Fase 0). Las fases 3–5 dependen de ellas.

| # | Decisión | Mi recomendación | Necesita saber |
|---|---|---|---|
| **D1** | Modelo(s) candidato(s) para el Revisor y cómputo | Probar primero el mismo proveedor con un modelo distinto al del Redactor (FW-4 propone «otra familia», pero es propuesta, no requisito) y medirlo con `reviewer_calibration` en `--mode live`. | Qué cómputo/proveedores hay. |
| **D2** | ¿Búsqueda externa (OpenAlex/EuropePMC) ya o después? | **Ya, al empezar la Fase 4.** Es lo que resuelve de raíz el problema de las fuentes sin DOI (DEC-4): las referencias nacen con identificador en vez de intentar recuperarlo después. | — |
| **D3** | Perfil de reporte para PR-FW-001 | El más simple que ejercite V03/V09: **revisión narrativa**; las sistemáticas exigen V07/V08 (Fase 4). | Qué tipo de documento era PR-FW-001. |
| **D4** | Quién es el autor humano aprobador en las pruebas | Una persona distinta de quien lanza el pipeline (la regla de AC8): p. ej. Pantoja o Molina como revisor asignado. | Quiénes. |
| **D5** | ¿Alcance de las fases 0–7, dejando las Capas A, B y C? | **Sí.** Ya hay una Fase 1 completa que probar antes de ampliar. | — |

Además sigue pendiente la **tarea 0.1** (archivar los artefactos de PR-FW-001): hacen falta el `article_id`, el texto publicado y lo que la traza no guarda.

## D. Lo que no puedo verificar yo

- **Revisar los términos de uso de Crossref y OpenAlex** para enviar títulos de trabajos inéditos (FW §20.7): comprobación legal.
- **QA visual** de la interfaz y comportamiento con un LLM real: ver [la guía de verificación manual](../qa/spec-032-verificacion-manual.md).
- **Añadir la opción `E20`** al campo `Epic` del Project 8 y rellenarla en los 16 issues (el agente no puede sin borrar los valores existentes).
