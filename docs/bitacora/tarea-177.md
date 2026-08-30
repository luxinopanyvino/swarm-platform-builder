# Tarea #177 — T6.3 Pinear dependencias + lockfile/hashes

## 2026-08-17 10:05 — Completada ✅

- **Rama:** `sec/176-177-supply-chain` (junto con #176)
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #177`)
- **Spec/ADR:** SPEC-020, Épica E6. Criterio vinculante: **AC3**.
- **Dependencias:** **T6.2 (#176)**, resuelta en la misma rama por eso mismo.

### El punto de partida

`backend/requirements.txt` tenía **0 de 24 líneas con versión exacta**: todo
rangos `>=`. Una reconstrucción de la imagen hoy y otra mañana podían traer
versiones distintas de las 79 dependencias efectivas, sin que nada lo registrase.
El frontend ya tenía `package-lock.json` y la CI ya usaba `npm ci`, así que la
mitad JS de AC3 estaba cubierta.

### Qué se hizo

Convención de dos ficheros, la de pip-tools:

- **`requirements.in`** — lo que se edita a mano: los rangos aceptables.
- **`requirements.txt`** — el lock generado, con versión exacta y hashes de todos
  los artefactos. **79 paquetes, 1910 hashes.**

```
pip-compile --generate-hashes --no-strip-extras \
    --output-file requirements.txt requirements.in
```

Mantener el nombre `requirements.txt` para el lock es deliberado: Dockerfile, CI,
README y la guía de instalación siguen funcionando sin tocar nada, y quien haga
`pip install -r requirements.txt` por costumbre instala exactamente lo fijado.

**La CI y la imagen instalan con `--require-hashes`**, que hace que pip rechace
cualquier requisito sin hash y cualquier artefacto cuyo hash no coincida. Sin esa
opción el lock sería documentación: pip instalaría igual lo que el índice sirviera.

### La verificación que de verdad importaba

Pinear a la última versión de todo es cambiar de versión, no solo escribirla. Así
que el lock se instaló en un **venv limpio de Python 3.12** —la misma versión que
usan CI y Docker— y se pasó la suite entera contra esas versiones exactas:

```
python3.12 -m venv /tmp/verifyenv
pip install --require-hashes -r requirements.txt     # 17 s, sin fallos de hash
DEBUG=true SECRET_KEY=… python -m pytest -q          # → 316 passed
```

Sin ese paso, esta tarea habría fijado 79 versiones que nadie ejecutó nunca.

### Decisiones documentadas

- **Se compila con Python 3.12**, no con el 3.11 del entorno de trabajo: los
  marcadores de entorno y la resolución dependen de la versión, y un lock hecho con
  otra puede omitir una rueda que allí hace falta. Está escrito en la cabecera de
  `requirements.in` para que nadie lo recompile con lo que tenga a mano.
- **`--no-strip-extras`**: se conservan `uvicorn[standard]`,
  `python-jose[cryptography]` y `passlib[bcrypt]` tal cual. Con extras eliminados el
  fichero sigue siendo instalable, pero se pierde la intención de por qué está cada
  cosa.
- **`requirements-dev.txt` (raíz) no se lockea**: es tooling local (`graphifyy`), la
  CI no lo instala y no llega a ningún despliegue. Fijarlo con hashes daría fricción
  sin ganar nada.
- **`pytest` y `pytest-asyncio` siguen dentro del lock de runtime**, donde ya
  estaban. Separar test de runtime es un cambio de estructura razonable, pero es
  otra tarea: mezclarlo aquí enturbiaría el diff del pineado.

### Test nuevo

`backend/tests/test_supply_chain.py` (17 casos, compartidos con #176). Para AC3:
- fuente y lock son ficheros distintos, y el lock está **generado**, no escrito a
  mano (cabecera de `pip-compile`);
- **ninguna** línea del lock sin versión exacta, y **ningún** paquete sin
  `--hash=sha256:`;
- todo lo declarado en `requirements.in` aparece en el lock — si alguien añade y no
  recompila, el lock se quedaría corto en silencio;
- el lock trae transitivas de sobra, que es lo que `--require-hashes` exige;
- **la CI instala con `--require-hashes` y no desde `requirements.in`**, y el
  frontend con `npm ci` y no `npm install`.

Ese último grupo es el que evita que el pineado quede de adorno: un lock perfecto
con un `pip install -r requirements.in` en el workflow no protege de nada.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_supply_chain.py -q
# → 17 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 333 passed
python scripts/validate_specs.py    # → [OK]
```

### Definition of Done (AC3)

- [x] **AC3** — dependencias pineadas con lockfile y hashes (backend con
  `pip-compile --generate-hashes`, frontend con `package-lock.json`), y la CI
  instala desde el lock, no desde rangos.
- [x] Tests que cubren el cambio, en verde (17 nuevos; 333 en la suite).
- [x] Docs: bloque de dependencias en `CLAUDE.md` y cabecera de `requirements.in`.
- [x] Sin secretos en el diff.
- [x] Rama con prefijo `sec/` hacia `develop`.

### Seguimiento

Cuando Dependabot abra su primera PR de backend tendrá que regenerar el lock. Si no
puede hacerlo de forma coherente, la PR **falla en la instalación** en lugar de
colar una versión sin verificar — que es el comportamiento que se busca, pero
conviene saberlo la primera vez que pase.
