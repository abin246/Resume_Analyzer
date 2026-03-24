# AI Resume Analyzer Pro

Full-stack ATS + semantic resume analyzer.

- Frontend: React (Vite)
- Backend: FastAPI
- LLM: LocalAI (OpenAI-compatible)
- Persistence: SQLite

## Deploy Target

- Frontend + Backend: Render
- LocalAI: Hyperstack VM

## Files Added for Deployment

- `render.yaml` (Render blueprint for backend + frontend)
- `backend/.env.render.example` (Render backend env template)
- `frontend/.env.render.example` (Render frontend env template)
- `hyperstack/docker-compose.localai.yml` (LocalAI stack for Hyperstack)
- `hyperstack/README.md` (Hyperstack LocalAI steps)

## Render Setup

### 1) Backend Service (Render Web Service)

Render uses `render.yaml`:

- `rootDir: backend`
- Build: `pip install -r requirements.txt`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Persistent disk at `/var/data`

Set backend env vars (from `backend/.env.render.example`):

- `LOCALAI_BASE_URL=https://<your-hyperstack-localai-domain>/v1`
- `LOCALAI_MODEL=meta-llama-3.1-8b-instruct`
- `MAX_RESUME_FILE_SIZE_MB=5`
- `ENABLE_FALLBACK_ANALYZER=true`
- `DATABASE_PATH=/var/data/resume_analyzer.db`
- `ALLOWED_ORIGINS=https://<your-render-frontend-domain>`

### 2) Frontend Service (Render Static Site)

- `rootDir: frontend`
- Build: `npm ci && npm run build`
- Publish dir: `dist`

Set frontend env var:

- `VITE_API_BASE_URL=https://<your-render-backend-domain>`

## Hyperstack LocalAI Setup

Use:

```bash
cd hyperstack
docker compose -f docker-compose.localai.yml up -d
```

Then verify:

```bash
curl http://127.0.0.1:8080/v1/models
```

Expose this service via your Hyperstack networking / reverse proxy with TLS.
Use that URL in Render backend `LOCALAI_BASE_URL`.

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
- User data privacy is scoped by `X-User-Id` (frontend sends a stable browser-local ID automatically).
