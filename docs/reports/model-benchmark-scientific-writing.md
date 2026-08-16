# Benchmark comparativo de modelos — redacción científica (SPEC-025)

Generado automáticamente por `evals/model_benchmark/run_benchmark.py` el 2026-08-09 20:13.

Métricas: `avg_score` (calidad, checks deterministas 0-100 por tarea — ver `dataset.py`), `elapsed_s` (latencia), `words/s` (proxy de throughput), `ram_mb`/`vram_mb` (huella del modelo cargado vía `GET /api/ps` de Ollama).

### Limitaciones metodológicas (leer antes de interpretar la tabla)

1. **Una sola muestra por modelo/tarea.** No se fija `temperature=0` (para reflejar el uso real de producción), así que cada llamada es algo no-determinista; una repetición podría variar el `avg_score`/latencia unos puntos. Tratar los números como orientativos, no como verdad absoluta — sobre todo cuando dos modelos quedan muy cerca.
2. **Dato corregido — `qwen2.5:3b` / redactor.** La corrida original registró `elapsed_s: 26791.54` (~7.4h) en esa única celda porque el equipo entró en suspensión a mitad de la llamada (ver bitácora de la sesión); no es cómputo real. Se corrigió a continuación excluyendo ese dato de los promedios y dejando la celda marcada. El `avg_score` de esa tarea (93.3) **sí** es válido — la suspensión afectó el reloj, no la respuesta del modelo.
3. **`citas_estilo_apa` da 0 en los 7 modelos.** Se verificó que el regex detecta correctamente el patrón `(Autor, Año)` — el 0 universal es una señal real: los modelos tienden a mover las citas a la lista de Referencias y dejar el cuerpo sin marcadores en texto, en vez de reformatear las citas in-text como pedía la consigna. No mide estilo narrativo (`Autor (Año) muestra...`). Antes de usar esta columna para decidir, conviene revisar manualmente 1-2 salidas reales.
4. **`llama3-chatqa:70b` (40GB) no es viable en este hardware** (12GB RAM, sin GPU dedicada): Ollama rechazó cargarlo (`failed to allocate buffer of size 38.5GB`) en las 4 tareas, ~15s cada intento — sin colgar el sistema. Queda documentado como referencia, fuera de la selección.

## Resumen por modelo

| Modelo | Score calidad medio | Latencia media (s) | Palabras/s media | RAM/VRAM media (MB) | Errores |
|---|---|---|---|---|---|
| `llama3.2:1b` | 68.7 | 46.9 | 6.0 | 1500.0 | 0/4 |
| `gemma2:2b` | 83.4 | 70.4 | 4.1 | 1872.0 | 0/4 |
| `qwen2.5:3b` | 81.3 | 79.2¹ | 1.75¹ | 2123.0 | 0/4 |
| `llama3.2:3b` | 62.5 | 119.8 | 2.1 | 2576.0 | 0/4 |
| `mistral:7b` | 82.5 | 272.4 | 0.8 | 4962.0 | 0/4 |
| `llama3:8b` | 87.5 | 306.9 | 0.8 | 5230.0 | 0/4 |
| `llama3-chatqa:latest` | 84.2 | 213.2 | 0.7 | 5230.0 | 0/4 |
| `llama3-chatqa:70b` | 0.0 (no viable) | 15.1 | — | — | 4/4 |

¹ Recalculado excluyendo la celda contaminada de redactor (ver limitación #2).

## Rol: investigador (sintesis_investigacion)

| Modelo | avg_score | elapsed_s | words/s | RAM/VRAM (MB) | cobertura_fuentes | longitud_adecuada |
|---|---|---|---|---|---|---|
| `llama3.2:1b` | 60.0 | 75.87 | 2.5 | 1652.9 | 20.0 | 100.0 |
| `gemma2:2b` | 100.0 | 93.15 | 1.85 | 1978.3 | 100.0 | 100.0 |
| `qwen2.5:3b` | 100.0 | 110.42 | 1.22 | 2300.4 | 100.0 | 100.0 |
| `llama3.2:3b` | 100.0 | 157.01 | 1.36 | 2974.9 | 100.0 | 100.0 |
| `mistral:7b` | 100.0 | 314.5 | 0.49 | 5441.7 | 100.0 | 100.0 |
| `llama3:8b` | 100.0 | 346.02 | 0.72 | 5710.3 | 100.0 | 100.0 |
| `llama3-chatqa:latest` | 100.0 | 249.72 | 0.38 | 5710.3 | 100.0 | 100.0 |
| `llama3-chatqa:70b` | ERROR | 15.61 | — | — | — | — |

## Rol: redactor (redaccion_borrador)

| Modelo | avg_score | elapsed_s | words/s | RAM/VRAM (MB) | cita_fuentes | longitud_adecuada | secciones_presentes |
|---|---|---|---|---|---|---|---|
| `llama3.2:1b` | 66.7 | 78.17 | 7.97 | 1448.9 | 0.0 | 100.0 | 100.0 |
| `gemma2:2b` | 93.3 | 137.72 | 4.44 | 1836.8 | 100.0 | 100.0 | 80.0 |
| `qwen2.5:3b` | 93.3 | N/D¹ (26791.54 en bruto — suspensión del equipo, no real) | N/D¹ | 2063.9 | 100.0 | 100.0 | 80.0 |
| `llama3.2:3b` | 100.0 | 255.43 | 2.42 | 2442.9 | 100.0 | 100.0 | 100.0 |
| `mistral:7b` | 80.0 | 531.48 | 0.85 | 4801.7 | 100.0 | 100.0 | 40.0 |
| `llama3:8b` | 100.0 | 589.4 | 0.94 | 5070.3 | 100.0 | 100.0 | 100.0 |
| `llama3-chatqa:latest` | 86.7 | 442.08 | 0.89 | 5070.3 | 100.0 | 100.0 | 60.0 |
| `llama3-chatqa:70b` | ERROR | 17.18 | — | — | — | — | — |

## Rol: revisor (revision_estructurada)

| Modelo | avg_score | elapsed_s | words/s | RAM/VRAM (MB) | esquema_correcto | json_valido |
|---|---|---|---|---|---|---|
| `llama3.2:1b` | 100.0 | 13.25 | 7.17 | 1448.9 | 100.0 | 100.0 |
| `gemma2:2b` | 100.0 | 23.82 | 5.12 | 1836.8 | 100.0 | 100.0 |
| `qwen2.5:3b` | 100.0 | 52.82 | 2.08 | 2063.9 | 100.0 | 100.0 |
| `llama3.2:3b` | 0.0 | 41.06 | 2.7 | 2442.9 | 0.0 | 0.0 |
| `mistral:7b` | 100.0 | 118.22 | 1.09 | 4801.7 | 100.0 | 100.0 |
| `llama3:8b` | 100.0 | 200.54 | 0.71 | 5070.3 | 100.0 | 100.0 |
| `llama3-chatqa:latest` | 100.0 | 72.27 | 0.68 | 5070.3 | 100.0 | 100.0 |
| `llama3-chatqa:70b` | ERROR | 13.84 | — | — | — | — |

## Rol: formateador (formateo_citas_apa)

| Modelo | avg_score | elapsed_s | words/s | RAM/VRAM (MB) | citas_estilo_apa | cuerpo_preservado |
|---|---|---|---|---|---|---|
| `llama3.2:1b` | 48.2 | 20.26 | 6.32 | 1448.9 | 0.0 | 96.4 |
| `gemma2:2b` | 40.2 | 27.09 | 5.06 | 1836.8 | 0.0 | 80.4 |
| `qwen2.5:3b` | 32.1 | 74.36 | 1.96 | 2063.9 | 0.0 | 64.3 |
| `llama3.2:3b` | 50.0 | 25.7 | 1.75 | 2442.9 | 0.0 | 100.0 |
| `mistral:7b` | 50.0 | 125.56 | 0.76 | 4801.7 | 0.0 | 100.0 |
| `llama3:8b` | 50.0 | 91.68 | 0.89 | 5070.3 | 0.0 | 100.0 |
| `llama3-chatqa:latest` | 50.0 | 88.57 | 0.88 | 5070.3 | 0.0 | 100.0 |
| `llama3-chatqa:70b` | ERROR | 13.78 | — | — | — | — |

## Selección (AC2)

> **Recomendación borrador asistida por IA, pendiente de ratificación de la
> comisión** (SPEC-025 AC2). Basada en una sola corrida por modelo/tarea (ver
> limitación #1) — tratarla como punto de partida, no como decisión cerrada.
> `llama3-chatqa:70b` queda excluido de toda recomendación (no viable en este
> hardware, ver limitación #4).

- **Investigador:** `gemma2:2b` — la tarea de síntesis satura la calidad
  (`avg_score` 100.0 en 6 de 7 modelos), así que el criterio decisivo es
  cómputo: `gemma2:2b` es el más rápido (93.15s) y liviano (1978MB) del grupo
  con score perfecto, ~3.4× más rápido que el `mistral:7b` que usa hoy el
  Investigador con fuentes. Alternativa si se prioriza robustez sobre
  velocidad: `qwen2.5:3b` (también 100.0, algo más lento).

- **Redactor:** `llama3.2:3b` — score perfecto (100.0) empatado solo con
  `llama3:8b`, pero con menos de la mitad de su latencia (255s vs 589s) y RAM
  (2443MB vs 5070MB). **Coincide con el modelo que ya usa hoy el Redactor en
  producción** — el benchmark valida la elección actual en vez de sugerir un
  cambio.

- **Revisor:** `llama3.2:1b` — score perfecto (100.0) y, por lejos, el más
  barato del grupo con score perfecto (13.25s, 1449MB). **Hallazgo a
  investigar antes de decidir:** el modelo que usa hoy el Revisor en
  producción, `llama3.2:3b`, **sacó 0.0 en esta corrida** — no devolvió JSON
  válido en el esquema esperado (`json_valido`/`esquema_correcto` ambos 0).
  Con una sola muestra no se puede concluir que sea un fallo sistemático, pero
  es una señal de riesgo real sobre el modelo actualmente en producción que
  amerita repetir la prueba (varias corridas) antes de tocar nada — no
  cambiar solo por este dato aislado, pero tampoco ignorarlo.

- **Formateador:** `llama3.2:3b` — dentro del grupo con `cuerpo_preservado`
  perfecto (100.0: `llama3.2:3b`, `mistral:7b`, `llama3:8b`,
  `llama3-chatqa:latest`), es el más rápido por lejos (25.7s vs 88-126s de
  los demás) y el más liviano (2443MB vs 4800-5070MB). Mejora marginal sobre
  el `llama3.2:1b` actual en preservación del cuerpo (100.0 vs 96.4) a un
  costo de latencia modesto (+5.4s). **Ninguno de los 7 modelos formatea bien
  las citas in-text** (limitación #3) — antes de aplicar este cambio conviene
  revisar manualmente 1-2 salidas reales de `llama3.2:3b` en esta tarea.

### Próximos pasos antes de aplicar (T13.4)

1. Confirmación de la comisión sobre esta selección (o ajustes).
2. Repetir la prueba del Revisor (varias corridas) antes de decidir si se
   mantiene `llama3.2:3b` o se reemplaza — es el único hallazgo con señal de
   riesgo, no solo de optimización.
3. Revisión manual de 1-2 salidas de Formateador antes de confiar en el
   cambio de modelo, dado el punto ciego de la métrica de citas in-text.
