# Medición real de AC3 — resolución de referencias contra Crossref y OpenAlex

- **Fecha:** 2026-10-21
- **Spec:** [SPEC-032](../specs/SPEC-032-publication-gate-framework.md) AC3 · [ADR-0011](../adr/0011-publication-gate-fail-closed.md)
- **Cómo se midió:** `scripts/measure_reference_resolution.py`, con el resolutor del producto tal cual (misma puerta de salida y los umbrales de `template.yaml`) y el conjunto `backend/evals/reference_resolution/references.jsonl`. Red real, 38 referencias, una consulta tras otra.
- **Límite que importa:** el conjunto lo escribió una persona **de memoria** (20 trabajos conocidos, citados como se citan a mano). Una discrepancia puede ser un error del conjunto y no del resolutor. Y 20 referencias es una muestra pequeña: **el 90 % medido es exactamente 18/20, sin margen**. No generaliza a un corpus real de la revista.

## Resultado

| Qué se mide | Resultado | Objetivo |
|---|---|---|
| Válidas **con DOI** | **18/20 (90 %)** | ≥ 90 % |
| Válidas **sin DOI** (título + autores) | 10/12 (83 %) | sin objetivo fijado |
| Controles negativos bloqueados (inventadas o alteradas) | **6/6** | 100 % (ninguna falsa aceptación) |

**El fallo grave —aceptar una referencia falsa— no ocurrió:** un DOI inventado, un título plausible inventado, autores cambiados, año cambiado, revista cambiada y un nombre de archivo, todo bloqueado.

## Qué enseñó la medición (y se corrigió)

La primera pasada dio **17/20 (85 %) y 8/12 sin DOI**: no cumplía. Los registros simulados de los tests no habían visto dos rigideces del resolutor:

1. **La revista se comparaba demasiado literal.** «Proc. IEEE Conf. Computer Vision and Pattern Recognition» frente a «2016 IEEE Conference on Computer Vision and Pattern Recognition» fallaba por «Proc.» y por el año. Ahora la comparación ignora palabras genéricas (*proceedings, conference, annual, international…*) y números, tolera el orden y las abreviaturas, y exige que coincida al menos el 60 % de las palabras significativas. Sigue distinguiendo «Nature» de «Science».
2. **Dos registros plausibles se daban por ambiguos sin intentar desempatar.** Watson y Crick (1953) aparecía con otro DOI de 1974. Ahora, si varios encajan por título y autores, el **año y la revista de la cita desempatan**; si tras eso siguen varios, o ninguno, queda `not_verified` y no se elige al azar.

Con las dos correcciones: **18/20 (90 %) con DOI, 10/12 (83 %) sin DOI, 6/6 negativos**. Los tests offline de `backend/tests/test_reference_measurement.py` fijan ambas correcciones.

## Lo que sigue sin pasar, y por qué

| Referencia | Causa | ¿Arreglable en el resolutor? |
|---|---|---|
| `vaswani-2017` (DOI arXiv) | OpenAlex da `publication_year` 2025 para ese DOI; la cita dice 2017. | No sin romper la regla de AC3 (año exacto, ±1 solo preprint↔publicada). Es calidad del dato de la fuente. |
| `devlin-2018` (DOI arXiv) | OpenAlex devuelve **otra obra** (primer autor «Kefallinos, Dionysios») para ese DOI. | No: el DOI apunta a un registro erróneo en OpenAlex. |
| `cortes-1995` sin DOI | Dos DOI distintos para la misma obra (`10.1007/bf00994018` y `10.1023/a:1022627411411`) con el mismo año y revista. | Falla cerrado, que es lo correcto: no se elige entre dos DOI. Pasa si la cita lleva DOI. |
| `vaswani-2017` sin DOI | Registros con DOI «raros» sin año ni revista coincidentes. | Falla cerrado. |

**Los dos fallos con DOI son de arXiv.** Esos DOI (`10.48550/arXiv.*`) los emite **DataCite**, no Crossref: Crossref responde 404 y todo recae en OpenAlex, cuya cobertura de preprints es la más débil de la muestra. Ver decisión DEC-1 en [spec-032-decisiones-pendientes.md](spec-032-decisiones-pendientes.md).

## Detalle por referencia

| id | tipo | resultado | motivo |
|---|---|---|---|
| `lecun-2015` | valid_with_doi | passed | — |
| `he-2016` | valid_with_doi | passed | — |
| `silver-2016` | valid_with_doi | passed | — |
| `mnih-2015` | valid_with_doi | passed | — |
| `hochreiter-1997` | valid_with_doi | passed | — |
| `krizhevsky-2017` | valid_with_doi | passed | — |
| `watson-1953` | valid_with_doi | passed | — |
| `cortes-1995` | valid_with_doi | passed | — |
| `breiman-2001` | valid_with_doi | passed | — |
| `hinton-2006` | valid_with_doi | passed | — |
| `schmidhuber-2015` | valid_with_doi | passed | — |
| `vaswani-2017` | valid_with_doi | failed | año: 2017 frente a 2025 |
| `devlin-2018` | valid_with_doi | failed | título: similitud 0.27 < 0.90; autores: el primer autor del registro es «Kefallinos, Dionysios» |
| `kingma-2014` | valid_with_doi | passed | — |
| `brown-2020` | valid_with_doi | passed | — |
| `esteva-2017` | valid_with_doi | passed | — |
| `jumper-2021` | valid_with_doi | passed | — |
| `page-2021` | valid_with_doi | passed | — |
| `wilkinson-2016` | valid_with_doi | passed | — |
| `ioannidis-2005` | valid_with_doi | passed | — |
| `lecun-2015-sin-doi` | valid_without_doi | passed | — |
| `he-2016-sin-doi` | valid_without_doi | passed | — |
| `silver-2016-sin-doi` | valid_without_doi | passed | — |
| `mnih-2015-sin-doi` | valid_without_doi | passed | — |
| `hochreiter-1997-sin-doi` | valid_without_doi | passed | — |
| `krizhevsky-2017-sin-doi` | valid_without_doi | passed | — |
| `watson-1953-sin-doi` | valid_without_doi | passed | — |
| `cortes-1995-sin-doi` | valid_without_doi | not_verified | varios candidatos igualmente plausibles (10.1007/bf00994018, 10.1023/a:1022627411411) |
| `breiman-2001-sin-doi` | valid_without_doi | passed | — |
| `hinton-2006-sin-doi` | valid_without_doi | passed | — |
| `schmidhuber-2015-sin-doi` | valid_without_doi | passed | — |
| `vaswani-2017-sin-doi` | valid_without_doi | not_verified | varios candidatos por título y autores y ninguno coincide en año y revista |
| `falsa-doi-inventado` | fabricated | failed | el DOI 10.1038/nature99999999 no existe en Crossref ni en OpenAlex |
| `falsa-titulo-plausible` | fabricated | not_verified | ninguna coincidencia fiable por título y autores |
| `falsa-autores-cambiados` | altered | failed | autores: el primer autor del registro es «LeCun» |
| `falsa-anio-cambiado` | altered | failed | año: 1999 frente a 2015 |
| `falsa-revista-cambiada` | altered | failed | revista: «Science» frente a «Nature» |
| `falsa-solo-nombre-de-archivo` | fabricated | not_verified | sin DOI ni título y autores con los que buscar |

## Cómo repetirla

```bash
cd backend
DEBUG=true SECRET_KEY=local-medicion python ../scripts/measure_reference_resolution.py --contact tu@correo.org --json informe.json
```

Sale con código 1 si no se llega al 90 % o si algún control negativo pasa. Conviene repetirla con un conjunto **revisado por la persona responsable de la revista** y con referencias de su campo real (preprints, español, informes técnicos) antes de dar AC3 por verificado.
