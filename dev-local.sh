#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
DOCS_DIR="$ROOT_DIR/docs"
VENV_DIR="$BACKEND_DIR/.venv"

printf "\n[info] Configurando entorno de desarrollo local\n"

cd "$BACKEND_DIR"
mkdir -p data
if [ ! -f "$VENV_DIR/bin/python" ]; then
  printf "[info] Creando entorno virtual en %s\n" "$VENV_DIR"
  python3 -m venv "$VENV_DIR" || python -m venv "$VENV_DIR"
fi

if [ ! -f "$VENV_DIR/bin/python" ]; then
  printf "[error] No se pudo crear el entorno virtual. Comprueba que Python 3 esté instalado.\n"
  exit 1
fi

source "$VENV_DIR/bin/activate"

printf "[info] Instalando dependencias de backend...\n"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

cd "$ROOT_DIR"

if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  printf "[error] No se encontró el frontend en %s\n" "$FRONTEND_DIR"
  exit 1
fi

cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
  printf "[info] Instalando dependencias de frontend...\n"
  npm install
fi

cd "$ROOT_DIR"

if command -v docker >/dev/null 2>&1; then
  printf "[info] Iniciando Qdrant con Docker Compose...\n"
  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose up -d qdrant
  else
    docker compose up -d qdrant
  fi
else
  printf "[warning] Docker no está instalado. Qdrant no podrá iniciarse automáticamente.\n"
fi

printf "[info] Iniciando backend...\n"
cd "$BACKEND_DIR"
DATABASE_URL="sqlite+aiosqlite:///./data/dev.db" \
SECRET_KEY="local-dev-secret" \
DEBUG=true \
ENABLE_DEV_ROLE_PROMOTION=true \
"$VENV_DIR/bin/uvicorn" app.main:app --reload --port 8000 > "$ROOT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

printf "[info] Iniciando frontend...\n"
cd "$FRONTEND_DIR"
npm run dev -- --host 0.0.0.0 > "$ROOT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

if [ -f "$DOCS_DIR/package.json" ]; then
  printf "[info] Iniciando docs VitePress...\n"
  cd "$DOCS_DIR"
  npx vitepress dev > "$ROOT_DIR/docs.log" 2>&1 &
  DOCS_PID=$!
fi

printf "\n[success] Servicios iniciados:\n"
printf "  Qdrant:   http://localhost:6333\n"
printf "  Backend:  http://127.0.0.1:8000\n"
printf "  Frontend: http://localhost:5173\n"
if [ -f "$DOCS_DIR/package.json" ]; then
  printf "  Docs:     http://localhost:5174\n"
fi
printf "\n[info] Logs locales:\n"
printf "  backend:  %s/backend.log\n" "$ROOT_DIR"
printf "  frontend: %s/frontend.log\n" "$ROOT_DIR"
if [ -f "$DOCS_DIR/package.json" ]; then
  printf "  docs:     %s/docs.log\n" "$ROOT_DIR"
fi
printf "\n[info] Usar 'tail -f backend.log frontend.log' para ver la salida en esta terminal.\n"
printf "[info] Para detener los servidores, finaliza los procesos %s y %s con kill.\n" "$BACKEND_PID" "$FRONTEND_PID"
