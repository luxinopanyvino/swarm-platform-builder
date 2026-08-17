# Tarea #168 — T4.1 Adoptar Alembic (reemplazar ALTER caseros)

## 2026-08-17 08:55 — Completada ✅

- **Rama:** `feat/168-alembic`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #168`)
- **Spec/ADR:** SPEC-018, Épica E4. Criterio vinculante: **AC1**.
- **Dependencias:** ninguna. Alembic ya estaba en `requirements.txt` sin usarse.

### Qué se hizo

**`backend/alembic/` + `alembic.ini`** (plantilla async). La URL **no** vive en
`alembic.ini`: `env.py` la toma de `settings.DATABASE_URL`, la misma que usa la
aplicación. Dos fuentes de verdad de la conexión son dos formas de migrar la base
equivocada — y una credencial versionada.

**`0001_baseline`**: foto del esquema actual, autogenerada desde `Base.metadata` y
ajustada a mano en un punto (ver decisiones).

**`0002_enum_labels`**: repara las etiquetas del enum nativo de Postgres (ver
«Fallo encontrado»).

**`init_db` reescrito**: ya no hay `create_all` ni `ALTER TABLE`. Aplica
`alembic upgrade head` reutilizando la conexión abierta —receta oficial para
invocar Alembic desde código async; sin ella el `asyncio.run` de `env.py`
reventaría dentro del bucle de eventos de la app— y en Postgres toma un
`pg_advisory_xact_lock` antes de migrar, para que varios workers no compitan por
el mismo DDL.

### Fallo encontrado por el camino

`ScientificFormat` no declara `values_callable`, así que SQLAlchemy almacena el
**nombre** del miembro: las etiquetas del enum nativo son `APA`, `IEEE`,
`VANCOUVER`, `CHICAGO`, `NATURE`, `NONE` — en mayúscula.

Los `ALTER` que había en `init_db` añadían `'chicago'` y `'nature'` **en
minúscula**: etiquetas que el ORM nunca usa, mientras que las que necesitaba no se
añadieron nunca. **En una base Postgres, guardar un artículo con formato Chicago o
Nature falla hoy** con `invalid input value for enum scientificformat`. No se veía
porque aquellas sentencias corrían dentro de un `try/except: pass`.

Es exactamente el fallo que motiva esta tarea, así que se arregla aquí:
`0002_enum_labels` registra las etiquetas correctas en las bases existentes (una
base nueva ya nace bien desde la base), y hay un test que impide la reincidencia.

### Decisiones documentadas

- **El ciclo `users` ↔ `projects` se rompe a mano.** Autogenerate emitía
  `projects` —con su FK a `users`— antes de crear `users`. SQLite tolera la
  referencia adelantada; **Postgres no**. La base crea `users` sin esa FK y la
  añade al final, cuando ambas tablas existen. Es el único ajuste manual a lo
  autogenerado, y está anotado en el docstring de la migración.
- **`compare_type` solo fuera de SQLite.** SQLite no tiene tipo UUID: las 25
  columnas UUID se emiten como `NUMERIC` y vuelven así al reflejarlas, de modo que
  `compare_type=True` marcaría un cambio de tipo espurio en cada `autogenerate`.
  En Postgres sí aporta, así que se decide por dialecto en lugar de apagarlo.
- **`fileConfig(..., disable_existing_loggers=False)`.** El valor por defecto de
  `fileConfig` desactiva todos los loggers ya creados: una invocación de Alembic en
  el mismo proceso dejaría **muda a la aplicación**, incluido el logging
  estructurado de T5.1. Lo descubrí porque un test pasaba solo y fallaba dentro del
  fichero — `alembic check` silenciaba al logger que el test siguiente observaba.
- **Las bases anteriores a Alembic se sellan, no se reejecutan.** Ya tienen las
  tablas pero no `alembic_version`; aplicarles la base fallaría con «table already
  exists». `init_db` detecta el caso y hace `stamp 0001_baseline`.
- **Y al sellar se avisa de las divergencias.** Como los ALTER corrían en
  `try/except: pass`, una base puede haber quedado coja en silencio. Sellarla sin
  más congelaría esa divergencia, así que se compara el esquema real con los
  modelos y se registra un `WARNING` con lo que falta. Es honesto sobre lo que la
  adopción de Alembic **no** puede arreglar retroactivamente.
- **`0002` lleva la etiqueta `ACL` aunque el enum de esta rama no la declare.** La
  añade #281 y una etiqueta sin usar es inerte; al revés —el ORM con un miembro que
  el tipo nativo no conoce— es un error al escribir. Por eso el test compara con
  `⊆` y no con `==`.
- **No se toca `dev.db`**: es T4.2 (#169), tarea aparte de la misma épica.

### Test nuevo

`backend/tests/test_migrations.py` (13 casos):
- **AC1 / paridad**: el esquema migrado es **igual** al de `create_all` — tablas,
  columnas con nulabilidad, índices, únicos y destino de las FK. Es la prueba que
  pide el plan de la spec. `alembic check` confirma que no hay cambios pendientes.
- **AC1 / sin DDL ad hoc**: se analiza el **AST** de `database.py` (no el texto:
  sus comentarios *hablan* de los ALTER que había) buscando literales con
  `ALTER TABLE` / `ALTER TYPE` / `CREATE TABLE` y llamadas a `create_all`.
- **`init_db`**: crea el esquema desde cero y llega a *head*; es idempotente.
- **Bases preexistentes**: se sellan conservando los datos; y si el esquema está
  incompleto, se avisa nombrando lo que falta (`event=alembic_stamp_divergence`).
- **Árbol de revisiones**: una sola cabeza (dos significan ramas paralelas), la
  base es la revisión de sellado, y `downgrade base` no deja tablas del modelo.
- **Etiquetas de enum**: las del ORM están cubiertas por la migración, y son
  nombres en mayúscula. Es la invariante que habría cogido `chicago`/`nature`.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_migrations.py -q
# → 13 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 258 passed
alembic upgrade head && alembic check     # → "No new upgrade operations detected."
python scripts/validate_specs.py          # → [OK]
```

Arranque en limpio: 10 tablas y `alembic_version = 0002_enum_labels`.

### Definition of Done (AC1)

- [x] **AC1** — el esquema se aplica mediante migraciones Alembic versionadas en el
  repo; `init_db` no ejecuta DDL ad hoc; despliegue limpio y migrado llegan al
  mismo esquema (con test de paridad que lo comprueba).
- [x] Tests que cubren el cambio, en verde (13 nuevos; 258 en la suite).
- [x] Docs: `backend/alembic/README` y el bloque de comandos de `CLAUDE.md`.
- [x] Sin secretos ni PII; sin dependencias nuevas (Alembic ya estaba pineado).
- [x] Rama con prefijo `feat/` hacia `develop`.

### Seguimiento

- **#169 (T4.2)**: `backend/dev.db` sigue trackeado, con hashes de los usuarios de
  desarrollo. Siguiente tarea natural de E4.
- **#170 (T4.3)**: el advisory lock de migración es un anticipo de lo que esa tarea
  necesita para el estado en memoria multi-worker.
- El residuo de etiquetas en minúscula (`chicago`, `nature`, `acl`) queda en el
  tipo de Postgres: no se pueden quitar sin recrear el tipo y reescribir las
  columnas que lo usan. Está anotado en `0002` para quien lea el tipo en producción.
