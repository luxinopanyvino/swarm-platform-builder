# Despliegue de la revista pública en Hostinger (hosting compartido)

Esta guía publica **solo la sección pública** (la revista) en un hosting
compartido de Hostinger (cPanel/hPanel: estáticos + PHP + MySQL). La plataforma
completa (generación con agentes + Ollama + Postgres) sigue corriendo **en
local**; aquí solo publicamos los artículos ya generados.

## Arquitectura

```
LOCAL (tu PC)                          HOSTINGER (compartido + dominio)
plataforma completa  ── publish ──►    public_html/
Postgres (verdad)      (HTTPS+token)     ├─ index.html + assets   (build público)
                                         ├─ api/magazine.php       (lee MySQL)
                                         ├─ api/ingest.php         (escribe MySQL)
                                         ├─ api/_pdo.php           (helper)
                                         ├─ api/db.php             (secretos, NO en repo)
                                         └─ .htaccess
                                       MySQL: tabla `articles`
```

El frontend llama a `/api/v1/magazine`; el `.htaccess` lo reescribe a
`api/magazine.php`, así que **no hay que tocar el código del frontend**.

---

## 1. Preparar Hostinger (una vez)

1. **Dominio/subdominio**: apunta tu dominio (o crea un subdominio, p. ej.
   `revista.tudominio.com`) a la carpeta `public_html` correspondiente.
2. **SSL**: activa el certificado gratis (hPanel → Seguridad → SSL).
3. **MySQL**: hPanel → Bases de datos MySQL → crea base de datos, usuario y
   contraseña. Anota: nombre BD, usuario, contraseña, host (normalmente
   `localhost`).
4. **Crear la tabla**: hPanel → phpMyAdmin → pestaña SQL → pega y ejecuta
   [`hostinger/schema.sql`](../hostinger/schema.sql).
5. **Token de ingesta**: genera un secreto, p. ej. `openssl rand -hex 32`.

## 2. Configurar el PHP (en el servidor)

1. Copia [`hostinger/api/db.example.php`](../hostinger/api/db.example.php) a
   `public_html/api/db.php` **en el servidor** y rellena credenciales MySQL +
   `ingest_token`. (`db.php` está en `.gitignore`: nunca al repo.)
2. Sube también `api/magazine.php`, `api/ingest.php`, `api/_pdo.php` y el
   `.htaccess` (a `public_html/`).

## 3. Compilar y subir el frontend público

```bash
cd frontend
npm ci            # si no tienes node_modules
npm run build:public
```

Esto genera `frontend/dist-public/` con `index.html` + `assets/`. Sube **todo
el contenido** de `dist-public/` a `public_html/` (File Manager o SFTP).

> Same-origin: como el PHP vive en el mismo dominio, **no hace falta
> `VITE_API_URL`** (las llamadas son relativas a `/api/...`).

Estructura final en el servidor:

```
public_html/
├─ index.html
├─ assets/...
├─ .htaccess
└─ api/
   ├─ db.php          (secretos, solo en server)
   ├─ _pdo.php
   ├─ magazine.php
   └─ ingest.php
```

## 4. Publicar artículos desde local

Tras publicar artículos en la plataforma local:

```bash
export HOSTINGER_INGEST_URL="https://tudominio.com/api/ingest.php"
export HOSTINGER_INGEST_TOKEN="<el-mismo-token-que-en-db.php>"

python scripts/publish_to_hostinger.py --dry-run   # ver qué se enviaría
python scripts/publish_to_hostinger.py             # enviar
```

En Windows PowerShell:

```powershell
$env:HOSTINGER_INGEST_URL  = "https://tudominio.com/api/ingest.php"
$env:HOSTINGER_INGEST_TOKEN = "<token>"
python scripts/publish_to_hostinger.py
```

## 5. Verificar

1. `https://tudominio.com/magazine` muestra los artículos.
2. Recargar en `/magazine` no da 404 (SPA fallback OK).
3. `curl -X POST https://tudominio.com/api/ingest.php` sin token → 401.

---

## Datos que necesitas de Hostinger (resumen)

| Dato | Dónde se usa | ¿Va al repo? |
|------|--------------|--------------|
| Dominio/subdominio | apuntar a `public_html`, SSL | no |
| Host MySQL (normalmente `localhost`) | `api/db.php` | no |
| Nombre BD MySQL | `api/db.php` | no |
| Usuario MySQL | `api/db.php` | no |
| Contraseña MySQL | `api/db.php` | no |
| Token de ingesta (lo generas tú) | `api/db.php` + env local | no |
| Acceso File Manager o SFTP | subir archivos | no |
| Versión de PHP (8.x recomendado) | requisito (`array_is_list`, PDO) | no |

## Notas

- **Portadas/imágenes**: si `cover_url` apunta a tu local, súbelas también a
  `public_html` (o usa URLs absolutas accesibles públicamente).
- **PHP 8+**: `ingest.php` usa `array_is_list()` (PHP 8.1+). En PHP 7.x habría
  que sustituirlo.
- **Alternativa sin PHP de escritura**: Hostinger permite "Remote MySQL"
  (whitelist de IP); el script local podría escribir directo a MySQL. Es más
  simple en código pero menos robusto/seguro, por eso usamos el puente PHP.
