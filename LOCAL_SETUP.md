# Local Setup Guide

## Prerequisites

- Python 3.9+
- Node.js 18+
- npm

## Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize SQLite database
python init_db.py

# Start backend (port 8000)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

## Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server (port 5173)
npm run dev
```

Frontend runs at: http://localhost:5173

## Environment Variables

Create `backend/.env`:

```
DATABASE_URL=sqlite:///./omaha.db
SECRET_KEY=your-secret-key-here
TUSHARE_TOKEN=your-tushare-token
```

## Database

Local dev uses SQLite (`backend/omaha.db`). No external database needed.

To reset: `rm backend/omaha.db && cd backend && python init_db.py`

## Troubleshooting

**Port in use:**
```bash
lsof -i :8000   # find backend process
lsof -i :5173   # find frontend process
kill -9 <PID>
```

**Missing dependencies:**
```bash
cd backend && pip install -r requirements.txt
cd frontend && npm install
```
