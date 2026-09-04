"""Harness EDD del comportamiento de los agentes (SPEC-014 / E9 / T9.3).

Evalúa los agentes **de esta plataforma** —sus perfiles, sus prompts y el modelo
que usan con el `LLM_PROVIDER` activo—, no modelos *foundation*: esa es la
pregunta de `evals/model_benchmark/` (SPEC-025 / E13), y son esfuerzos distintos.

Ver `README.md` para el uso y para la diferencia entre los modos `live` y
`replay`, que es la parte del diseño que más importa no confundir.
"""
