# Omaha OntoCenter v2

Configuration-driven pricing analysis platform with ontology management and object exploration.

## Features

- User authentication and project management
- DataHub integration for metadata discovery
- YAML-based ontology configuration
- Object Explorer for querying business objects
- Multi-datasource support (PostgreSQL, MySQL)

## Quick Start

```bash
# Clone and setup
git clone <repository-url>
cd omaha_ontocenter_v2

# Copy environment template
cp .env.example .env

# Start with Docker
docker-compose up -d

# Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Documentation

See [Phase 1 Deployment Guide](docs/phase1-deployment.md) for detailed setup instructions.

## Architecture

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL
- **Frontend**: React 18 + TypeScript + Ant Design
- **Integration**: DataHub for metadata management
- **Core**: Omaha Core for configuration and query execution

## Development

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## License

MIT
