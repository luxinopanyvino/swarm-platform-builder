# Tarea #211 — T8.5 Independencia de proyectos: ProjectContext, scoping y namespace RAG

## 2026-09-03 — Completada ✅

- **Rama:** `feat/211-project-isolation`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #211`)
- **Spec/ADR:** SPEC-013, Épica E8, ADR-0005. Criterio vinculante: **AC6**.
- **Dependencias:** T8.1 (#237), ya integrada. **No** depende de T8.3, así que no
  interfiere con la cadena T8.3 → T8.4 → T8.6.

## Lo que había

No es que el aislamiento entre proyectos estuviera mal implementado: **no
existía**. La capa RAG no tenía ninguna noción de proyecto, y eso abría tres
puertas distintas al mismo problema.

**1. La colección salía del perfil del agente.** `rag_collection` por defecto es
`rag_docs` para todo el mundo. Dos proyectos creados desde la misma plantilla
nacen con el mismo `investigador` y el mismo `rag_docs`, así que sus documentos
caían en la **misma** colección de Qdrant y en el **mismo** bucket `agent_name`.
El pipeline de uno recuperaba los documentos del otro y los citaba como fuentes.

**2. Y `rag_collection` lo escribe la persona usuaria**, en el editor de agentes.
Aunque cada proyecto hubiera tenido su colección, bastaba con teclear la del
vecino para leerla.

**3. La consulta de perfiles de la ejecución no filtraba por proyecto:**

```python
select(AgentProfileModel).where(AgentProfileModel.slug.in_(agent_slugs))
```

`slug` no es único entre proyectos. El pipeline podía arrancar con el modelo, el
prompt, el `rag_collection` y los `rag_doc_ids` de **otro** proyecto, según el
orden que devolviera la base.

Y por el camino aparecieron cuatro fugas más de la misma familia:

- `GET /agents/rag/collections` y `GET /agents/rag/library` recorrían **todas** las
  colecciones de la instancia: cualquier sesión autenticada veía los nombres de
  fichero de todos los proyectos.
- `PUT` y `DELETE /agents/claude-defs/{id}` buscaban el perfil **solo por id**, sin
  comprobar a qué proyecto pertenece. Con el identificador de un perfil ajeno se
  podía reescribir su prompt o borrarlo.
- `DELETE /agents/rag/library/{collection}/{doc_id}` pasaba la colección de la ruta
  tal cual a Qdrant: un borrado con la colección del vecino borraba sus documentos.
- El documento de demo (`_seed_default_rag_document`) se sembraba en la colección
  común, que es justo lo que AC6 nombra como «ni del *seed* de demo se filtra».

## La forma de la solución

**El nombre de la colección se deriva, no se recibe.** `platform/project_context.py`
es el único sitio que lo compone: `p_<project_id>__<bucket>`, donde el *bucket* es
lo que aporta el perfil, saneado. Un bucket no puede salirse de su prefijo, así que
el aislamiento no depende de que nadie olvide un filtro — depende de que los datos
estén físicamente en otro sitio.

Eso resuelve de paso qué significa la «biblioteca compartida»: `__library__` es un
bucket más, así que queda compartida **dentro** del proyecto y no entre proyectos,
que es lo que la palabra debía haber significado.

**El proyecto viaja como dependencia, no como parámetro.** La cabecera
`X-Project-Id` la pone un interceptor de axios —un único sitio en el frontend— y la
resuelve `platform/project_access.py`, que además comprueba el acceso con las
mismas reglas que `projects.py`. Un parámetro más en cada firma se olvida en la
siguiente ruta que alguien añada; una dependencia, no. Y hay un test que analiza el
**AST** del router para que ninguna ruta con «rag» en el path se quede sin ella.

**En la ejecución, el proyecto sale del artículo, no de la cabecera.** El
aislamiento no puede depender de lo que mande el cliente. Un artículo sin proyecto
devuelve 409 en vez de caer al espacio común: sin proyecto no hay dónde aislar, y
negarse es lo correcto.

## Decisiones documentadas

- **Colección por proyecto y no filtro por `project_id` en el payload.** La spec
  permitía las dos. Con filtro, un `where` olvidado en una consulta futura vuelve a
  filtrar datos y no rompe nada visible; con colecciones separadas, el dato
  simplemente no está ahí. Para arreglar una fuga, la opción estructural gana a la
  que depende de la disciplina.
- **`404` y no `403` para un proyecto ajeno.** Un 403 confirmaría que ese
  identificador existe.
- **La migración atribuye lo heredado al proyecto del sistema.** Los puntos
  antiguos no llevan proyecto: no se puede reconstruir de quién era cada uno. En
  una instancia de un solo proyecto —el caso normal hoy— la atribución es exacta;
  en una con varios, esos documentos ya se estaban filtrando y el destino correcto
  no existe. Asignarlos al del sistema **cierra** la fuga y los demás vuelven a
  subir lo suyo. Fallar hacia el lado cerrado es lo contrario de lo que hacía el
  código anterior.
- **La migración copia y no borra.** `--drop-legacy` existe, pero como paso aparte
  y explícito, después de comprobar.
- **`routers/ai.py` también se acota.** Escribe en Qdrant por su cuenta, al margen
  de la capacidad RAG. Dejarlo fuera habría mantenido un escritor en la colección
  común, y el aislamiento valdría solo para la mitad de los caminos.
- **El camino sin proyecto sigue existiendo, pero avisa.** `collection_for_state`
  cae al nombre heredado si el estado no trae `project_id` y registra un `WARNING`.
  El endpoint de ejecución ya exige proyecto, así que solo debería darse en pruebas
  o en ejecuciones anteriores a esta versión.
- **`RequireProject` en el frontend.** El dashboard no estaba condicionado a tener
  proyecto activo: sin él, las llamadas ahora responden 400. Se redirige a la
  selección en vez de enseñar un error que no explica qué falta.

## Test nuevo

`backend/tests/test_project_isolation.py` (23 casos):

- **AC6 de extremo a extremo**: dos proyectos indexan en el bucket que sus perfiles
  llaman igual, y cada uno solo ve lo suyo a través de la API real.
- **El perfil no puede salirse**: parametrizado con lo que se puede teclear en el
  editor —la colección del vecino, `../../otro`, rutas con barras, vacío, `None`—;
  el resultado siempre queda dentro del proyecto.
- **Sin cabecera no se adivina** (400), un proyecto ajeno da 404 y uno inexistente
  también.
- **La ejecución usa el perfil de su proyecto**: se crean dos `investigador`
  homónimos con modelos distintos, el ajeno primero para que sea el que una
  consulta sin filtro encontraría antes.
- **Un artículo sin proyecto no ejecuta** (409).
- **Editar y borrar el perfil del vecino** devuelven 404 y lo dejan intacto.
- **Guardias estructurales**: análisis AST de que toda ruta RAG declara `project`,
  y de que los tres adapters resuelven su colección por `collection_for_state`.
- **La migración**: simulacro que no escribe, aplicación que copia sin destruir el
  original, y repetición que no duplica.

## Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 632 passed, 15 skipped (los 15 son los de Redis de #170, sin servidor aquí)

npm run build && npm run build:public     # → ambos OK
python3 scripts/validate_specs.py         # → [OK]
python3 scripts/check_contrast.py         # → [OK] 68 pares AA
python3 scripts/check_design_tokens.py    # → [OK]
python3 scripts/check_async_states.py     # → [OK]
```

## Definition of Done

- [x] **AC6** — dos proyectos con documentos distintos no se ven; ni entre ellos ni
  el *seed* de demo. Con migración para lo ya subido.
- [x] Tests que cubren el cambio, en verde (23 nuevos; 632 en la suite).
- [x] Builds de frontend en verde, las dos.
- [x] Docs: SPEC-013 anotada y `CLAUDE.md` con el contrato de aislamiento.
- [x] Sin secretos ni PII; sin dependencias nuevas.
- [x] Rama con prefijo `feat/` hacia `develop`.

## Seguimiento

- **Hay que ejecutar la migración al desplegar.** Sin ella, los documentos ya
  subidos dejan de verse: nada lee las colecciones heredadas.
  `python scripts/migrate_rag_namespaces.py --apply`.
- **`app/modules/ai/adapters/http.py` es código muerto** (nadie lo importa) y
  escribe en la colección común. Se ha dejado como estaba porque borrarlo no es
  esta tarea, pero si alguien lo monta reabre una fuga. Candidato a eliminación en
  T8.3, que reescribe esa zona.
- **AC6 acota a RAG.** Los checkpoints de LangGraph y el bus de eventos van por
  `article_id`, que ya es único; no se han tocado.
- **T8.3 (#209) sigue siendo el cuello de botella de E8**: desbloquea T8.4 y T8.6.
  Esta tarea le deja el `ProjectContext` que su `template.yaml` necesitará para
  saber en qué espacio vive cada proyecto.
