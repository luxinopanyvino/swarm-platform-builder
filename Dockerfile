FROM python:3.12-slim

WORKDIR /app

# Instalar dependencias del sistema esenciales para compilar ciertas librerías
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar requerimientos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente inicial
COPY . .

EXPOSE 8000

# El comando se sobreescribe en el docker-compose para usar --reload en desarrollo
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]