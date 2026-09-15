# Guía para colaboradores: «AlejandrIA por dentro»

Página interactiva para quien se incorpora al proyecto: qué es, su arquitectura, las
tareas abiertas en un Gantt sin fechas con sus dependencias y cómo trabajar (ejecutar
una tarea con `/resolve-task`, añadir tareas o épicas, regenerar la página).

- **Página generada:** `docs/public/onboarding/alejandria-por-dentro.html`. Se abre
  directamente en el navegador, y la web de documentación la sirve en
  `/onboarding/alejandria-por-dentro.html` (`cd docs && npm run dev`).
- **Generador:** `scripts/build_onboarding.py`.

## Regenerar

Desde la raíz del repositorio:

```bash
python scripts/build_onboarding.py               # estado de los issues desde GitHub (gh)
python scripts/build_onboarding.py --sin-github  # usa la copia docs/onboarding/issues.json
```

Regénerala después de `/sdd-sync --apply`, al mergear PRs que cierran tareas o al tocar
los YAML de este directorio. El cambio entra por una rama `docs/` con su PR.

## De dónde sale cada cosa

| Lo que muestra la página | Dónde se edita |
|---|---|
| Épicas, tareas, severidad, dependencias, «Hecha cuando» | `docs/specs/SPEC-*.md` (bloque `sdd-sync` y sección 3) |
| Número de issue y si está abierto o cerrado | GitHub; copia en `issues.json` |
| Alcance, archivos, «Ojo con», rama, revisión, nombre corto, reparto | `tareas.yaml` |
| Arquitectura, recorrido de una ejecución, agentes del pipeline | `arquitectura.yaml` |
| Estilos y comportamiento | `plantilla/estilos.css`, `plantilla/app.js` |

No dupliques en `tareas.yaml` lo que ya está en la spec: título, severidad, dependencias
y criterios se leen de allí, y así no pueden divergir.

## Coherencia

El generador avisa de fichas para tareas que ya no existen, componentes desconocidos,
criterios que faltan en la spec y tareas sin ficha. Con `--estricto`, todo salvo «sin
ficha» es error: así lo ejecuta `backend/tests/test_onboarding_page.py`.
