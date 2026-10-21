# Medición de AC3 con referencias reales de la revista (muestra mínima)

- **Fecha:** 2026-10-22 · **Herramienta:** `scripts/measure_reference_resolution.py --dataset backend/evals/reference_resolution/journal-sample.jsonl`
- **Resolutor:** el del producto, con red real (Crossref, OpenAlex y DataCite).
- **Complementa** [la medición con el conjunto de 38 referencias](medicion-ac3-spec-032.md), que se escribió de memoria. Esta usa lo que **de verdad hay en la revista**.

## Qué es la muestra, y qué no

Las referencias salen de los **5 artículos publicados** de la base de desarrollo (sección *Referencias* y fuentes guardadas en los informes de la compuerta).
Son **4 referencias distintas** (varias se repiten entre artículos). **Es real pero mínima**: sirve para ver cómo se comporta el resolutor con datos de la
revista, **no para estimar tasas**. Las expectativas (`expect`) son criterio del asistente y **no las ha revisado la persona responsable de la revista**.

## Resultado

| Referencia (como aparece en la revista) | Dato que trae | Resultado |
|---|---|---|
| Lin et al., *Agentic Harness Engineering…* | título y 11 autores, sin año ni DOI | ✅ pasa (búsqueda por título y autores) |
| Lin et al., la misma, como la guardó la compuerta | + DOI de arXiv, año 2026 | ✅ pasa (DataCite) |
| Lee, Chae, Park, *Harness Engineering for Physical AI…* | título y 3 autores, sin año ni DOI | ✅ pasa |
| *Lost in the Middle: How Language Models Use Long Contexts* | **solo el título** | ⚠️ `not_verified`: «sin DOI ni título y autores con los que buscar» |
| «Bienvenida Alejandria Magazine.» | **no es un trabajo científico** | ✅ bloqueada (`not_verified`), como debe |

Válidas con DOI: 1/1. Válidas sin DOI: 2/3. Negativos bloqueados: 1/1. (Cifras con muestra de 5; no son una tasa.)

## Hallazgos que importan

1. **Una referencia con solo el título no se puede verificar, y está publicada.** *Lost in the Middle* aparece así en 2 de los 5 artículos publicados.
   El resolutor exige título **y** autores (el primer autor debe coincidir: es lo que impide aceptar un trabajo distinto con título parecido) y no los
   tiene. Es el comportamiento correcto de la falla cerrada, pero con `gate_enforce: true` esos artículos no pasarían. Salidas: aportar el DOI a mano
   desde el panel (ya existe, #472) o que la búsqueda externa de la Fase 4 haga que las referencias **nazcan con identificador y autores**.
2. **Un enlace de bienvenida de la revista figura como referencia bibliográfica** en un artículo publicado. La compuerta lo bloquearía; hoy nada lo
   impedía. Es un defecto del Investigador/Redactor (mete fuentes que no son literatura), no del resolutor.
3. **Las fuentes del RAG llegan con metadatos muy desiguales:** en los informes guardados, la misma referencia aparece unas veces sin autores, año ni DOI
   (`not_verified`) y otras completa con DOI de arXiv (`passed`). Sin DOI ni autores no hay verificación posible; esto es lo que de verdad decide la tasa en
   producción, más que el resolutor.
4. **Una lista de autores incompleta sin «et al.» falla** (`solo coinciden 3 de 10`): ocurrió con una fila mía mal transcrita. Es la regla de AC3 funcionando;
   se anota porque en citas escritas a mano ocurrirá.

## Qué sigue faltando

Una muestra **suficiente** y **revisada por la persona responsable** (decenas de referencias de varios artículos, con su veredicto esperado). Esta base de
desarrollo no la tiene; hace falta el corpus real de la revista. El conjunto está en `backend/evals/reference_resolution/journal-sample.jsonl` y el mismo
script lo mide cuando crezca.
