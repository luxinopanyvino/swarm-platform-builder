# Tarea #166 — T3.4 Compose dev/prod separados; TLS; cabeceras + CSP en nginx

## 2026-08-30 12:50 — Completada ✅

- **Rama:** `sec/166-compose-tls-csp`
- **PR:** pendiente → `develop` (la abre el mantenedor con `Closes #166`)
- **Spec/ADR:** SPEC-017, Épica E3. Criterio vinculante: **AC4**.
- **Dependencias:** **#165 (T3.3)**, mergeada. Aquella sacó la configuración de
  nginx a un fichero; aquí es donde eso paga.

### Qué se hizo

**`docker-compose.prod.yml`** como override del base (que es el de desarrollo):
sin `--reload`, `DEBUG=false`, sin bind mount del código, sin publicar el puerto
del backend, con TLS y con `nginx.prod.conf`.

**`frontend/security-headers.inc`** con las cabeceras y la CSP, **compartido por
dev y prod**. Una CSP que solo se aplica en producción es una CSP que se descubre
rota en producción.

**`frontend/nginx.prod.conf`** con TLS 1.2/1.3, redirección 301 desde HTTP y HSTS.

**Pasarela `/api/` en nginx**, que es lo que hace posible el resto: el cliente pasa
a llamar con rutas relativas (`VITE_API_URL` vacío), desaparece el origen cruzado y
la CSP puede quedarse en `connect-src 'self'`, lo más estricto posible. En
producción, además, el tráfico de API viaja por el mismo TLS sin un segundo
certificado.

### Lo que encontró la verificación con navegador

La CSP no se escribió «a ojo»: se construyó la aplicación, se sirvió con **estas
cabeceras exactas** y se cargó en Chromium. La primera versión rompía la interfaz:

```
Refused to load the stylesheet 'https://fonts.googleapis.com/css2?family=Source+Serif+4…'
because it violates the following Content Security Policy directive: "style-src 'self' 'unsafe-inline'"
```

`ds/colors_and_type.css` hace `@import url(fonts.googleapis.com…)` para Source Serif
4, Source Sans 3 y JetBrains Mono. **No aparece en `index.html`**, así que ni el
grep ni la revisión del build lo habrían delatado: solo lo dice el navegador. Con
la CSP inicial la plataforma habría salido a producción con las fuentes caídas al
sistema, sin un solo error visible.

Hacen falta **los dos** dominios: `fonts.googleapis.com` sirve el CSS y
`fonts.gstatic.com` los ficheros de fuente. Con uno solo se carga la hoja y ninguna
fuente.

Tras el arreglo, con la aplicación cargada bajo la CSP definitiva:

```json
{ "hijosDeRoot": 2,
  "estilos": { "font": "\"Source Sans 3\", system-ui…" },
  "iframe": { "estiloEnLinea": "rgb(1, 2, 3)", "imagenDataURI": true },
  "violacionesCSP": [], "erroresJS": [] }
```

La última línea del iframe importa: es la maqueta del paper, que lleva su CSS en un
`<style>` en línea y sus figuras como data URI (T11.5). Ambas cosas siguen
funcionando bajo la política.

### Decisiones documentadas

- **`script-src 'self'`, sin `'unsafe-inline'`.** Es la directiva que de verdad
  para un XSS, y se puede permitir el lujo porque el build de Vite no emite scripts
  en línea (comprobado sobre `dist/index.html`).
- **`style-src` sí lleva `'unsafe-inline'`, y conviene saber por qué**: la interfaz
  usa `style={{…}}` de React por todas partes y la maqueta del paper lleva un
  `<style>`. Quitarlo dejaría la aplicación sin estilos. No es descuido, es el
  precio de esa arquitectura de estilos.
- **Etiquetas `!override` en el compose de producción.** Compose *fusiona* listas:
  sin ellas no habría forma de **quitar** el bind mount del código, que seguiría
  ahí anulando la imagen inmutable y devolviendo los permisos del host a un proceso
  que desde T3.3 no corre como root. Exige Compose ≥ 2.24, y está dicho en el
  fichero.
- **HSTS solo en producción.** Enviarla por HTTP dejaría al navegador incapaz de
  volver a abrir el sitio en local durante un año.
- **8443 y no 443 dentro del contenedor**: el proceso sin privilegios de T3.3 no
  puede abrir puertos bajos. El compose publica `443:8443`.
- **`proxy_buffering off` en `/api/`**: el pipeline emite por SSE y con búfer la
  ejecución parece congelada hasta que termina.
- **`X-Request-ID` se propaga** por la pasarela; sin eso se pierde la correlación
  de T5.1 y el audit log de T6.4 deja de poder cruzarse con los logs.
- **Los `.pem` van a `.gitignore`**: una clave privada versionada es una clave
  comprometida, aunque sea de preproducción.

### Test nuevo

`backend/tests/test_deploy_tls_csp.py` (35 casos): existe el override y **cambia
algo** —se comprueba que dev sí lleva `--reload` y prod no—; producción apaga
`DEBUG` y la promoción de rol, deja de montar el código del host **sin perder los
volúmenes que deben persistir**, y no publica el puerto del backend; TLS con 1.2/1.3
y sin versiones viejas, redirección 301, HSTS solo en prod, claves fuera de git;
las cinco cabeceras declaradas, con `always` —sin él nginx no las envía en las
respuestas de error, que son las que más falta hace proteger— y compartidas por
ambos entornos; la CSP con `script-src` estricto, los permisos que la maqueta del
paper necesita, los dominios de fuentes que la aplicación **realmente** carga y las
directivas que cierran los agujeros de siempre; y la pasarela, con SSE sin búfer y
la cabecera de correlación.

### Verificación

```
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest tests/test_deploy_tls_csp.py -q
# → 35 passed
DEBUG=true SECRET_KEY=ci-secret-not-for-prod python -m pytest -q
# → 469 passed
npm run build && npm run build:public   # ambos OK
python scripts/validate_specs.py        # → [OK]
```

Y la aplicación construida, cargada en Chromium bajo las cabeceras reales: **0
violaciones de CSP, 0 errores de JavaScript**.

### Lo que NO se ha podido verificar

Como en #165, **no hay Docker en el entorno de trabajo**: el TLS y la pasarela no
se han ejercitado dentro de contenedores. Antes de mergear:

```bash
# certificado de prueba: docs/guide/tls-local.md
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl -I  http://localhost/     # → 301 hacia https
curl -kI https://localhost/    # → 200 + cabeceras de seguridad
```

### Definition of Done (AC4)

- [x] **AC4** — compose dev y prod separados (prod sin `--reload` ni `DEBUG`) y
  nginx con TLS, cabeceras de seguridad y CSP.
- [x] Tests que cubren el cambio, en verde (35 nuevos; 469 en la suite).
- [x] Docs: `docs/guide/tls-local.md`.
- [x] Sin secretos en el diff; claves TLS excluidas de git.
- [x] Rama con prefijo `sec/` hacia `develop`.
- [ ] **Pendiente de verificación con Docker real** (ver arriba).

### Cierre de la épica E3

Con T3.4, **E3 (Infraestructura y despliegue) queda completa**: Qdrant autenticado
y puertos internos (T3.1), sin credenciales en el compose (T3.2), contenedores sin
root e imagen slim (T3.3), compose dev/prod con TLS y CSP (T3.4), y límites de
recursos con healthchecks de readiness (T3.5).

### Seguimiento

**Autoalojar las fuentes** en lugar de traerlas de Google: quitaría dos dominios de
la CSP, una dependencia de terceros y el envío de la IP de cada visitante a Google.
Encaja con el trabajo de tokens de diseño de **E7 (#192)**.
