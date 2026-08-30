#!/usr/bin/env python3
"""Sonda de readiness para el healthcheck del contenedor (SPEC-017 / T3.5 / AC5).

Un fichero y no un `python -c` embebido en el compose: aquel acababa siendo comillas
anidadas atravesando YAML, shell y Python, imposible de leer y fácil de romper sin
que nadie se entere —un healthcheck averiado no avisa, simplemente deja de proteger.
Así además se puede probar.

Se usa Python y no `curl`/`wget` porque es lo único que la imagen del backend
garantiza tener; T3.3 (#165) va a quitarle el toolchain.

Salida: `0` si el backend está listo para atender tráfico, `1` en cualquier otro
caso —incluido el `503` de readiness, que es una respuesta válida y no un error.
"""
import os
import sys
import urllib.error
import urllib.request

URL = os.environ.get("HEALTHCHECK_URL", "http://localhost:8000/health/ready")
TIMEOUT = float(os.environ.get("HEALTHCHECK_TIMEOUT", "5"))


def is_ready(url: str = URL, timeout: float = TIMEOUT) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.status == 200
    except urllib.error.HTTPError:
        return False   # 503: vivo pero no listo
    except Exception:
        return False   # no arrancado, sin red, timeout…


if __name__ == "__main__":
    sys.exit(0 if is_ready() else 1)
