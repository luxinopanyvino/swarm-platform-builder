# Tarea #169 — T4.2 Sacar dev.db de git + .gitignore

## 2026-08-17 09:25 — Completada ✅

- **Rama:** `chore/169-untrack-dev-db`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #169`)
- **Spec/ADR:** SPEC-018, Épica E4. Criterio vinculante: **AC2**.
- **Dependencias:** ninguna. Complementa #168 (T4.1), ya mergeada.

### Qué se hizo

`git rm --cached backend/dev.db` y reglas de `.gitignore` **generales** (`*.db`,
`*.sqlite`, `*.sqlite3` y los auxiliares `*.db-journal` / `-wal` / `-shm`) en
lugar de las dos por directorio que había.

### El fichero trackeado no era el que se usa

Lo primero que salió al mirar: hay **dos** bases en el repo y la versionada no es
la buena.

| Fichero | Estado | Uso real |
|---|---|---|
| `backend/data/dev.db` | 184 KB, del día | **la que usa la app** (`config.yaml`: `sqlite+aiosqlite:///./data/dev.db`), ya ignorada |
| `backend/dev.db` | 172 KB, **del 3 de agosto** | **huérfana**: ninguna configuración apunta ahí |

`backend/dev.db` es un residuo de haber arrancado alguna vez desde otro directorio.
Llevaba **más de dos semanas congelado** y con el esquema anterior a media docena
de migraciones, así que quien lo abriese leería una base que ya no existe — además
de los hashes de contraseña de `admin@admin`, `redactor@example.com` y
`revisor@example.com`.

Por eso las reglas nuevas son generales y no por directorio: las anteriores solo
cubrían `backend/data/` y `backend/tests/`, y este fichero se coló justo por vivir
fuera de ambos.

### El clon nuevo estaba roto, y se arregla aquí

AC2 pide además que «el arranque en dev lo recree solo», y **no era cierto**:

- git no versiona directorios vacíos, y `backend/data/` no tenía nada trackeado;
- SQLite **no crea el directorio padre** — comprobado:
  `sqlite3.connect('/tmp/nodir_test/data/dev.db')` → `unable to open database file`.

O sea que un clon recién hecho arrancaba con ese error contra la ruta que
`config.yaml` indica. Untrackear `dev.db` no lo causaba, pero AC2 lo cubre, así que
va aquí. Dos capas:

1. **`backend/data/.gitkeep`** (versionado, explica por qué existe) para que el
   directorio sobreviva al clon.
2. **`_ensure_sqlite_directory`** en `database.py`: al arrancar con una URL SQLite,
   crea el directorio del fichero si falta. Así «se recrea sola» vale para
   **cualquier** ruta configurada, no solo para la que lleva el `.gitkeep`.

### Decisiones documentadas

- **`--cached`, no borrado.** El fichero se saca del índice pero se deja en disco:
  es la copia local de quien clonó, y ahora está ignorada. Destruir datos locales
  no es asunto de esta tarea.
- **El historial no se reescribe.** `git rm --cached` quita el binario de HEAD, no
  del historial: sigue siendo recuperable en commits antiguos. No se propone un
  `filter-repo` porque las credenciales son las de desarrollo por defecto
  (`admin123` y compañía, documentadas en el README) y reescribir el historial de
  `develop` rompería todos los clones. **Si esas contraseñas se hubiesen usado en
  algún sitio real, esto no bastaría** — queda dicho, no escondido.
- **Reglas globales en vez de por directorio**, precisamente por lo que pasó.
  `Thumbs.db` sigue con su línea propia más arriba; ahora es redundante, pero
  quitarla mezclaría un cambio de Windows en una tarea de bases de datos.

### Test nuevo

`backend/tests/test_no_tracked_databases.py` (13 casos):
- **Ningún** fichero con extensión de base está trackeado (`git ls-files`).
- `git check-ignore` —la única fuente fiable, porque interpreta el fichero como
  git— cubre seis rutas representativas: la que estaba trackeada, la real de
  desarrollo, las de los tests, un arranque desde la raíz, un `.sqlite3` suelto y
  un auxiliar `-wal`.
- `backend/data/` sobrevive a un clon (hay algo trackeado dentro).
- El arranque crea el directorio que falta; con base **en memoria** es un no-op y
  no revienta.
- **De cero a base usable**: en un subproceso limpio, con `DATABASE_URL` apuntando
  a un directorio inexistente, `init_db` crea el fichero y lo deja migrado (`users`
  y `alembic_version` presentes). Es AC2 de punta a punta.

Comprobado que el guardarraíl sirve: contra el índice de `develop`,
`git ls-files --with-tree=develop` devuelve `backend/dev.db` — el primer test
habría fallado antes del cambio.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_no_tracked_databases.py -q
# → 13 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 316 passed
python scripts/validate_specs.py          # → [OK]
git ls-files | grep -Ei '\.(db|sqlite3?)$'   # → (ninguno)
```

### Definition of Done (AC2)

- [x] **AC2** — `dev.db` y cualquier `*.db` local fuera del control de versiones y
  excluidos por `.gitignore`; el arranque en dev recrea la base **y su directorio**.
- [x] Tests que cubren el cambio, en verde (13 nuevos; 316 en la suite).
- [x] Sin secretos nuevos en el diff; el binario con hashes sale de HEAD.
- [x] Rama con prefijo `chore/` hacia `develop`.

### Seguimiento

Con T4.1 y T4.2, de **E4** queda solo **#170 (T4.3)**: externalizar a Redis el
estado en memoria (`active_streams`, `active_tasks`, `pending_decisions`) para
poder correr varios workers. Depende de T3.2.
