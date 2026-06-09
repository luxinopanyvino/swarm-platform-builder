# Instalación local

## Requisitos previos

- Python 3.12+
- Node.js 20+
- [Ollama](https://ollama.com/) instalado y ejecutándose
- [Qdrant](https://qdrant.tech/) binario descargado

## 1. Preparar el backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## 2. Configurar variables de entorno

Copia el archivo de ejemplo y edítalo:

```bash
cp .env.example backend/.env.local
```

Variables mínimas para desarrollo:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/dev.db
SECRET_KEY=<genera con: python -c "import secrets; print(secrets.token_hex(32))">
DEBUG=true
ENABLE_DEV_ROLE_PROMOTION=true

LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text

QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=rag_docs
RAG_VECTOR_SIZE=768
```

Para usar **OpenAI** en lugar de Ollama:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
# OPENAI_BASE_URL=   # dejar vacío para OpenAI; rellenar para Azure / Groq / vLLM
```

## 3. Descargar modelos Ollama

```bash
ollama pull nomic-embed-text   # embeddings (obligatorio)
ollama pull llama3.2           # LLM por defecto
```

## 4. Arrancar Qdrant

Ejecutar desde la **raíz del proyecto** (Qdrant usa `./storage` por defecto):

```bash
# Windows
.\qdrant\qdrant.exe
# Linux / macOS
./qdrant/qdrant
```

## 5. Arrancar el backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

## 6. Arrancar el frontend

```bash
cd frontend
npm install
npm run dev
```

## Arranque unificado (Windows)

El script `dev-local.cmd` levanta Qdrant, backend y frontend en una sola ventana:

```bat
dev-local.cmd
```

## Puertos por defecto

| Servicio | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| Ollama | http://localhost:11434 |
| Docs (VitePress) | http://localhost:5174 |

## Docker Compose

```bash
docker compose up --build
```
