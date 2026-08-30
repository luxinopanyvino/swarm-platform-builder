# ─────────────────────────────────────────────────────────────
# Etapa 1: compilar dependencias (SPEC-017/T3.3/AC3)
# ─────────────────────────────────────────────────────────────
# El toolchain vive SOLO aquí. Cualquier dependencia que necesite compilarse lo
# hace en esta etapa, y la imagen final no hereda ni el compilador ni las
# cabeceras de desarrollo: menos superficie y nada con lo que construir un
# binario si alguien llega a ejecutar código en el contenedor.
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Instalación desde el lock con hashes (SPEC-020/T6.3): --require-hashes hace que
# pip rechace cualquier artefacto cuyo hash no coincida.
# --prefix aísla el árbol instalado para copiarlo entero a la etapa final.
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.txt

# ─────────────────────────────────────────────────────────────
# Etapa 2: imagen final — sin toolchain y sin root
# ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Usuario sin privilegios. UID/GID fijos para que el propietario de los volúmenes
# no dependa de en qué orden los cree el sistema.
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

# Solo el árbol de paquetes ya instalado; el compilador se queda en la etapa 1.
COPY --from=builder /install /usr/local

COPY --chown=app:app . .

# Directorios que la aplicación escribe en runtime. Se crean aquí y con dueño
# `app` porque un volumen nombrado hereda el propietario del directorio que
# monta: si no existiera con estos permisos, Docker lo crearía como root y el
# proceso no root no podría escribir en él.
RUN mkdir -p /app/app/.rag_local /app/app/.assets /app/logs \
 && chown -R app:app /app/app/.rag_local /app/app/.assets /app/logs

USER app

EXPOSE 8000

# El healthcheck del compose invoca `python healthcheck.py` (SPEC-017/AC5): esta
# imagen tiene Python por definición, así que la sonda sigue funcionando aunque
# aquí ya no haya wget ni curl.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
