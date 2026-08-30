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

# Etapa 2: Servidor de producción, sin root (SPEC-017/T3.3/AC3)
#
# Imagen sin privilegios de NGINX Inc.: corre como el usuario `nginx` (UID 101) y
# trae ya preparados los directorios temporales y de caché que nginx necesita
# escribir. Hacerlo a mano sobre `nginx:alpine` obliga a repartir permisos en
# media docena de rutas, y basta olvidar una para que el contenedor arranque y
# falle al primer request.
FROM nginxinc/nginx-unprivileged:1.25-alpine

# Copiar archivos compilados al directorio de Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuración de la SPA como ficheros (ver frontend/nginx.conf).
# Las cabeceras y la CSP van aparte porque las comparten dev y prod.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY security-headers.inc /etc/nginx/conf.d/security-headers.inc

# 8080: un proceso sin privilegios no puede abrir el 80.
EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]