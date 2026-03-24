# AI Resume Analyzer Pro

Full-stack ATS + semantic resume analyzer.

- Frontend: React (Vite)
- Backend: FastAPI
- LLM: LocalAI (OpenAI-compatible)
- Persistence: SQLite

## Deploy Target (Render Only)

- Frontend: Render Static Site
- Backend: Render Web Service
- LocalAI: Render Private Service (`pserv`, Docker)

## Deployment Files

- `render.yaml` (all three services)
- `backend/.env.render.example` (backend env template)
- `frontend/.env.render.example` (frontend env template)
- `localai_render/Dockerfile` (LocalAI private service image)
- `localai_render/models/tinyllama-chat.yaml` (sample model config)

## Render Setup

### 1) LocalAI Private Service

`render.yaml` defines:

- `type: pserv`
- `name: resume-analyzer-localai`
- Docker context: `localai_render`
- Persistent disk mounted at `/models`

Important:

- Add your model files + YAML config under `/models` on the mounted disk.
- Keep backend `LOCALAI_MODEL` in sync with model name.

### 2) Backend Web Service

`render.yaml` defines:

- `rootDir: backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Disk mounted at `/var/data`

Backend env values:

- `LOCALAI_BASE_URL=http://resume-analyzer-localai:8080/v1`
- `LOCALAI_MODEL=tinyllama-chat`
- `MAX_RESUME_FILE_SIZE_MB=5`
- `ENABLE_FALLBACK_ANALYZER=true`
- `DATABASE_PATH=/var/data/resume_analyzer.db`
- `ALLOWED_ORIGINS=https://<your-render-frontend-domain>`

### 3) Frontend Static Site

`render.yaml` defines:

- `rootDir: frontend`
- Build: `npm ci && npm run build`
- Publish: `dist`

Frontend env value:

- `VITE_API_BASE_URL=https://<your-render-backend-domain>`

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

## Notes

- If LocalAI is unavailable, deterministic fallback still runs analysis.
- User data privacy is scoped by `X-User-Id` (frontend sends stable browser-local ID).
