# Etapa 1: Construcción/Compilación
FROM node:20-alpine AS builder

WORKDIR /app

# Copiar manifiestos e instalar dependencias usando npm ci para mayor estabilidad
COPY package*.json ./
RUN npm ci --include=dev

# Copiar código fuente y generar la carpeta dist
COPY . .

# URL de API para compilar en el frontend (React/Vite)
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL:-http://localhost:8000}

# Compilar
RUN npm run build

# Etapa 2: Servidor de producción
FROM nginx:1.25-alpine

# Copiar archivos compilados al directorio de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Copiar configuración personalizada de Nginx para manejar rutas de SPA (React Router)
RUN echo 'server { \
    listen 80; \
    location / { \
        root /usr/share/nginx/html; \
        index index.html index.htm; \
        try_files $uri $uri/ /index.html; \
    } \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]