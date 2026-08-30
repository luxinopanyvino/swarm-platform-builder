# TLS en local para el compose de producción

El override de producción (`docker-compose.prod.yml`, SPEC-017/T3.4) sirve por
HTTPS y espera un certificado en `certs/`:

| Fichero | Qué es |
|---|---|
| `certs/fullchain.pem` | certificado + cadena |
| `certs/privkey.pem` | clave privada |

En un despliegue real los aporta el operador (una CA, o Let's Encrypt vía ACME).
Para **probar el arranque en local** basta con uno autofirmado:

```bash
mkdir -p certs
openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout certs/privkey.pem -out certs/fullchain.pem \
  -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
```

Y levantar:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl -k -I https://localhost/            # 200 + cabeceras de seguridad
curl -I http://localhost/                # 301 hacia https
```

> Los `.pem` están en `.gitignore`. **No los versiones**: una clave privada en git
> es una clave comprometida, aunque sea de preproducción.

## Lo que el navegador dirá

Un certificado autofirmado provoca un aviso de seguridad, y con **HSTS** activo
—que `nginx.prod.conf` envía— el navegador recordará durante un año que ese host
debe ir por HTTPS. En `localhost` eso puede estorbar después al desarrollar por
HTTP: se limpia en `chrome://net-internals/#hsts` (o el equivalente del navegador).

Por eso HSTS **solo** se envía en la configuración de producción; la de desarrollo
(`nginx.conf`) sirve por HTTP y no la manda.

## Terminación TLS por delante

Si ya hay un balanceador o un proxy que termina TLS (ALB, Cloudflare, Traefik…),
lo razonable es dejar que nginx sirva HTTP y no montar certificados aquí: en ese
caso se usa el compose base y se publica el 8080 detrás del balanceador. Lo que no
debe hacerse es terminar TLS dos veces sin necesidad.
