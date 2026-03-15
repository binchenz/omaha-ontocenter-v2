# Phase 1 Deployment Guide

## Overview

This guide covers the deployment of the Omaha OntoCenter Phase 1 system, which includes:
- User authentication and project management
- DataHub integration for metadata discovery
- Ontology configuration with YAML
- Object Explorer for querying business objects

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL 14+ (if not using Docker)
- DataHub instance running (optional for initial testing)
- Python 3.11+ (for local development)
- Node.js 18+ (for local development)

## Quick Start with Docker

1. Clone the repository and navigate to the project directory:
```bash
cd omaha_ontocenter_v2
```

2. Copy the environment template:
```bash
cp .env.example .env
```

3. Edit `.env` and set your configuration:
```bash
# Generate a secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Set DataHub URL if available
DATAHUB_GMS_URL=http://your-datahub-instance:8080
```

4. Start all services:
```bash
docker-compose up -d
```

5. Check service status:
```bash
docker-compose ps
```

6. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Local Development Setup

### Backend

1. Create a virtual environment:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up the database:
```bash
# Create PostgreSQL database
createdb omaha_db

# Run migrations
alembic upgrade head
```

4. Start the development server:
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Access the application at http://localhost:3000

## Database Migrations

### Create a new migration:
```bash
cd backend
alembic revision --autogenerate -m "description"
```

### Apply migrations:
```bash
alembic upgrade head
```

### Rollback migrations:
```bash
alembic downgrade -1
```

## Configuration

### Backend Configuration

Edit `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@host:port/database

# JWT Authentication
SECRET_KEY=your-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=30

# DataHub Integration
DATAHUB_GMS_URL=http://datahub-gms:8080
DATAHUB_GMS_TOKEN=optional-token

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend Configuration

The frontend uses Vite proxy configuration in `vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    },
  },
}
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get token
- `GET /api/v1/auth/me` - Get current user

### Projects
- `GET /api/v1/projects/` - List projects
- `POST /api/v1/projects/` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `PUT /api/v1/projects/{id}` - Update project
- `DELETE /api/v1/projects/{id}` - Delete project

### Ontology
- `POST /api/v1/ontology/validate` - Validate configuration
- `POST /api/v1/ontology/build` - Build ontology

### Query
- `POST /api/v1/query/{project_id}/query` - Query objects
- `GET /api/v1/query/{project_id}/objects` - List object types
- `GET /api/v1/query/{project_id}/history` - Get query history

### DataHub
- `GET /api/v1/datahub/search` - Search datasets
- `GET /api/v1/datahub/datasets/{urn}/schema` - Get dataset schema
- `GET /api/v1/datahub/datasets/{urn}/properties` - Get dataset properties

## Usage Guide

### 1. Register and Login

1. Navigate to http://localhost:3000/register
2. Create a new account
3. Login with your credentials

### 2. Create a Project

1. Click "New Project" button
2. Enter project name and description
3. Click "Create"

### 3. Configure Ontology

1. Click "Configure" on a project
2. Enter Omaha YAML configuration
3. Click "Validate" to check configuration
4. Click "Build Ontology" to verify it works
5. Click "Save" to persist configuration

Example configuration:
```yaml
client:
  name: "My Business"
  industry: "Retail"

datasources:
  - name: "main_db"
    type: "postgresql"
    connection:
      host: "localhost"
      port: 5432
      database: "mydb"
      username: "user"
      password: "${DB_PASSWORD}"

ontology:
  objects:
    - name: "Product"
      datasource: "main_db"
      table: "products"
      properties:
        - name: "id"
          type: "integer"
          column: "product_id"
        - name: "name"
          type: "string"
          column: "product_name"
        - name: "price"
          type: "decimal"
          column: "unit_price"
```

### 4. Query Objects

1. Navigate to the Explorer tab
2. Select an object type
3. Click "Query" to fetch data
4. View results in the table

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Connect to database
docker-compose exec postgres psql -U omaha -d omaha_db
```

### Backend Issues

```bash
# View backend logs
docker-compose logs backend

# Restart backend
docker-compose restart backend

# Check migrations
docker-compose exec backend alembic current
```

### Frontend Issues

```bash
# View frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose up -d --build frontend

# Clear node_modules
rm -rf frontend/node_modules
docker-compose up -d --build frontend
```

### DataHub Connection Issues

1. Verify DataHub is running and accessible
2. Check `DATAHUB_GMS_URL` in `.env`
3. Test connection:
```bash
curl http://your-datahub-instance:8080/health
```

## Security Considerations

### Production Deployment

1. Change the `SECRET_KEY` to a strong random value
2. Use environment variables for sensitive data
3. Enable HTTPS/TLS
4. Configure proper CORS origins
5. Use strong database passwords
6. Enable database SSL connections
7. Set `DEBUG=false` in production

### Database Security

```bash
# Use strong passwords
DATABASE_URL=postgresql://user:strong-password@host:port/database

# Enable SSL
DATABASE_URL=postgresql://user:password@host:port/database?sslmode=require
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready -U omaha
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

## Backup and Restore

### Database Backup

```bash
# Backup
docker-compose exec postgres pg_dump -U omaha omaha_db > backup.sql

# Restore
docker-compose exec -T postgres psql -U omaha omaha_db < backup.sql
```

## Scaling

### Horizontal Scaling

1. Use a load balancer (nginx, HAProxy)
2. Run multiple backend instances
3. Use external PostgreSQL with connection pooling
4. Configure session storage (Redis)

### Performance Optimization

1. Enable database query caching
2. Use CDN for frontend assets
3. Enable gzip compression
4. Optimize database indexes
5. Use connection pooling

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Review API documentation: http://localhost:8000/docs
- Check configuration: `.env` file
- Verify database migrations: `alembic current`
