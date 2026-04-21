# Running the App

## Start Services

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

## Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |

## Stop Services

Press `Ctrl+C` in each terminal, or:

```bash
lsof -i :8000 | awk 'NR>1 {print $2}' | xargs kill -9
lsof -i :5173 | awk 'NR>1 {print $2}' | xargs kill -9
```

## Demo Account

A demo account is available on the cloud instance at http://69.5.23.70:
- Username: `demo`
- Password: `test123`
