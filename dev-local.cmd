@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%backend"
set "FRONTEND_DIR=%ROOT_DIR%frontend"
set "VENV_DIR=%BACKEND_DIR%\.venv"
set "UVICORN_EXE=%VENV_DIR%\Scripts\uvicorn.exe"

echo.
echo Verificando entorno virtual en %VENV_DIR%...
pushd "%BACKEND_DIR%"
if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [info] Creando entorno virtual en %VENV_DIR%...
  python -m venv .venv
  if errorlevel 1 (
    popd
    echo [error] No se pudo crear el entorno virtual.
    exit /b 1
  )
)

if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate.bat"
) else (
  popd
  echo [error] No se encontro %VENV_DIR%\Scripts\activate.bat
  exit /b 1
)

echo [info] Instalando dependencias de backend...
"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  popd
  echo [error] Fallo la instalacion de dependencias.
  exit /b 1
)
popd

pushd "%BACKEND_DIR%"
if not exist "data" mkdir data
popd

if not exist "%UVICORN_EXE%" (
  echo [error] No se encontro %UVICORN_EXE%
  echo Crea el entorno virtual con: cd backend ^&^& python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
  exit /b 1
)

if not exist "%FRONTEND_DIR%\package.json" (
  echo [error] No se encontro el frontend en %FRONTEND_DIR%
  exit /b 1
)

set "FRONTEND_VITE_BIN=%FRONTEND_DIR%\node_modules\.bin\vite"
if not exist "%FRONTEND_VITE_BIN%" (
  echo [info] Instalando dependencias de frontend en %FRONTEND_DIR%...
  pushd "%FRONTEND_DIR%"
  npm.cmd install
  if errorlevel 1 (
    popd
    echo [error] Fallo la instalacion de dependencias de frontend.
    exit /b 1
  )
  popd
)

:: ── Qdrant (vector DB) ───────────────────────────────────────
echo.
echo Verificando Qdrant...
curl -sf http://localhost:6333/healthz >nul 2>&1
if not errorlevel 1 (
  echo [OK] Qdrant ya esta corriendo en http://localhost:6333
  goto :qdrant_ok
)

set "QDRANT_EXE=%ROOT_DIR%qdrant\qdrant.exe"
if not exist "%QDRANT_EXE%" set "QDRANT_EXE=C:\qdrant\qdrant.exe"

if not exist "%QDRANT_EXE%" goto :qdrant_missing
start "Qdrant" /D "%ROOT_DIR%" /min "%QDRANT_EXE%"
echo [OK] Qdrant iniciado ^(storage: %ROOT_DIR%storage^)
echo     Esperando 4s para que arranque...
ping -n 5 127.0.0.1 >nul
goto :qdrant_ok

:qdrant_missing
echo [AVISO] Qdrant no encontrado. La biblioteca vectorial no funcionara.
echo         Descarga qdrant.exe y ponlo en una de estas rutas:
echo           - %ROOT_DIR%qdrant\qdrant.exe  ^(recomendado, junto al proyecto^)
echo           - C:\qdrant\qdrant.exe
echo         Descarga: https://github.com/qdrant/qdrant/releases

:qdrant_ok

echo Iniciando backend en una nueva ventana...
set DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
set SECRET_KEY=local-dev-secret
set DEBUG=true
set ENABLE_DEV_ROLE_PROMOTION=true
REM Siembra de demo (SPEC-015/T1.6): crea admin@admin y los usuarios de
REM prueba. Sin este flag el arranque no siembra credenciales debiles.
set ENABLE_DEV_SEED=true
start "Alex Backend" /D "%BACKEND_DIR%" "%UVICORN_EXE%" app.main:app --reload --port 8000

echo Iniciando frontend en una nueva ventana...
start "Alex Frontend" /D "%FRONTEND_DIR%" npm.cmd run dev

set "DOCS_DIR=%ROOT_DIR%docs"
if exist "%DOCS_DIR%\package.json" (
  echo Iniciando docs ^(VitePress^) en una nueva ventana...
  start "Alex Docs" /D "%DOCS_DIR%" cmd /k "node node_modules\vitepress\bin\vitepress.js dev"
)

echo.
echo Qdrant:   http://localhost:6333
echo Backend:  http://127.0.0.1:8000
echo Frontend: http://localhost:5173
if exist "%DOCS_DIR%\package.json" (
  echo Docs:     http://localhost:5174
)
echo.
echo Si ya habia procesos corriendo en esos puertos, cierra esas ventanas y vuelve a ejecutar este script.

endlocal