FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema esenciales para compilar ciertas librerías
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos desde el lock con hashes (SPEC-020/T6.3).
# --require-hashes hace que pip rechace cualquier artefacto cuyo hash no coincida:
# la imagen no puede acabar con una versión distinta de la fijada, ni aunque el
# índice sirva otra cosa.
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

# Copiar el código fuente inicial
COPY . .

EXPOSE 8000

# El comando se sobreescribe en el docker-compose para usar --reload en desarrollo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]