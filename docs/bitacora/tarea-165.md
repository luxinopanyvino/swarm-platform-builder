# Tarea #165 — T3.3 Contenedores no-root + imagen backend slim

## 2026-08-30 12:15 — Completada ✅

- **Rama:** `sec/165-nonroot-containers`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #165`)
- **Spec/ADR:** SPEC-017, Épica E3. Criterio vinculante: **AC3**.
- **Dependencias:** ninguna. Toca la sonda que dejó **#167 (T3.5)**, y por eso hay
  un test que comprueba que Python sigue en la imagen final.

### Qué se hizo

**`backend/Dockerfile` → multi-stage.** El toolchain (`build-essential`) vive solo
en la etapa de compilación; la final copia el árbol de paquetes ya instalado
(`pip install --prefix=/install` + `COPY --from=builder`) y no hereda ni compilador
ni cabeceras. Se crea un usuario `app` (UID/GID 1001 fijos) y la imagen termina con
`USER app`. `wget`, que estaba solo para sondeos, desaparece: la sonda de T3.5 usa
Python, que en esta imagen está por definición.

**`frontend/Dockerfile` → `nginxinc/nginx-unprivileged:1.25-alpine`.** Corre como
`nginx` (UID 101) y trae ya preparados los directorios temporales y de caché que
nginx necesita escribir.

**`frontend/nginx.conf` (nuevo).** La configuración era un `RUN echo '...' >` con
barras invertidas: se escribía como root en tiempo de build —imposible con una
imagen sin privilegios— y era ilegible. Ahora es un fichero que se copia.

**`docker-compose.yml`**: el frontend publica `8080:8080` (antes `8080:80`) y su
healthcheck sigue al puerto nuevo. El puerto **del host no cambia**, así que
`ALLOWED_ORIGINS` y `VITE_API_URL` siguen valiendo.

### La parte que de verdad rompe: las rutas escribibles

Bajar de privilegios es fácil; lo que revienta después es escribir donde ya no se
puede. La aplicación escribe en tres sitios dentro de `/app`:

| Ruta | Qué guarda | Antes |
|---|---|---|
| `/app/app/.rag_local` | fallback local del RAG | ya era volumen |
| `/app/app/.assets` | figuras de los artículos (T11.5) | **dentro del bind mount** |
| `/app/logs` | logs del pipeline por artículo | **dentro del bind mount** |

Las dos últimas caían en `./backend:/app`, que trae los permisos del **host**: el
proceso sin privilegios no habría podido escribir. Ahora son volúmenes nombrados, y
los tres directorios se crean en la imagen con dueño `app` — un volumen nombrado
hereda el propietario del directorio que monta, así que si no existiera con esos
permisos Docker lo crearía como root y estaríamos igual.

El caso de `logs/` habría sido especialmente difícil de ver: `_flush_log_file`
captura la excepción y solo deja un `warning`, así que los logs del pipeline
habrían dejado de escribirse **en silencio**.

### Decisiones documentadas

- **Imagen sin privilegios en vez de repartir permisos a mano.** Hacerlo sobre
  `nginx:alpine` obliga a tocar media docena de rutas (`/var/cache/nginx`,
  `/var/run`, `/etc/nginx/conf.d`…), y basta olvidar una para que el contenedor
  arranque y falle al primer request.
- **nginx escucha en 8080**: por debajo de 1024 hace falta un privilegio que este
  contenedor ya no tiene.
- **`UID/GID` fijos (1001)**: si se dejan al azar, el propietario de los volúmenes
  depende del orden en que el sistema cree las cuentas.
- **`.dockerignore` ampliado** con `logs/`, `app/.assets/`, `app/.rag_local/`,
  `data/` y `tests/`: son datos de runtime y no tienen por qué acabar horneados en
  la imagen.
- **La verificación de hashes de T6.3 sigue en pie** tras el troceado, y hay un
  test que lo comprueba: era justo lo que un multi-stage mal hecho se lleva por
  delante.

### Lo que NO se ha podido verificar

**No hay Docker en el entorno de trabajo**, así que **la imagen no se ha
construido ni ejecutado**. Los tests leen los Dockerfiles y el compose; no
sustituyen a un `docker build`. Antes de mergear conviene:

```bash
docker compose build backend frontend
docker compose up -d
docker compose exec backend whoami     # → app
docker compose exec frontend whoami    # → nginx
docker compose ps                      # los dos, healthy
```

Es el riesgo principal de esta PR y se dice tal cual, en lugar de darlo por bueno.

### Test nuevo

`backend/tests/test_container_hardening.py` (27 casos): la imagen es multi-stage y
termina con un `USER` no root, creado con `useradd`, y **sin pasos privilegiados
después**; ninguna herramienta del toolchain aparece en la etapa final —y sí en la
del builder, para que el test mida algo—; la final copia del builder en vez de
reinstalar; se conserva `--require-hashes`; sigue habiendo Python para la sonda de
T3.5. En el frontend: corre sin privilegios, nginx escucha por encima de 1024, el
`try_files` de React Router sobrevivió a la reescritura, el compose publica el
puerto que nginx **realmente** escucha, el healthcheck apunta a ese mismo puerto y
el puerto del host no se movió. Y las rutas escribibles: cada una —**leída del
código, no de una lista a mano**— tiene volumen nombrado y se crea en la imagen con
`chown`.

Comprobado que el guardarraíl muerde: añadiendo `build-essential` a la etapa final,
`test_the_toolchain_never_reaches_the_final_image[build-essential]` falla.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_container_hardening.py -q
# → 27 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 434 passed
npm run build && npm run build:public   # ambos OK
python scripts/validate_specs.py        # → [OK]
```

### Definition of Done (AC3)

- [x] **AC3** — los contenedores corren con `USER` no root y la imagen final del
  backend no incluye `build-essential` ni toolchain.
- [x] Tests que cubren el cambio, en verde (27 nuevos; 434 en la suite).
- [x] Sin secretos en el diff.
- [x] Rama con prefijo `sec/` hacia `develop`.
- [ ] **Pendiente de verificación con Docker real** (ver arriba): no disponible en
  el entorno de trabajo.

### Seguimiento

De **E3** queda **#166 (T3.4)**: compose dev/prod separados, TLS y cabeceras de
seguridad + CSP. El `frontend/nginx.conf` que se crea aquí es justo donde van esas
cabeceras — antes había que escribirlas dentro de una cadena con barras invertidas.
