# ActorHub.ai - Startup Guide

## Prerequisites
- Docker Desktop (running)
- Node.js 18+
- Python 3.11+

## Quick Start (4 terminals needed)

### Terminal 1: Docker Services
```bash
cd "C:\ActorHub.ai 1.1"
docker-compose up -d
```

Wait for all services to be healthy:
```bash
docker ps
```

Expected: postgres, redis, minio, qdrant - all "healthy" or "Up"

### Terminal 2: API Server
```bash
cd "C:\ActorHub.ai 1.1\apps\api"
.\venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API will be available at: http://localhost:8000
API Docs: http://localhost:8000/docs

### Terminal 3: Frontend
```bash
cd "C:\ActorHub.ai 1.1\apps\web"
npm run dev
```

Frontend will be available at: http://localhost:3000

### Terminal 4: Celery Worker (for background tasks)
```bash
cd "C:\ActorHub.ai 1.1\apps\worker"
..\api\venv\Scripts\activate
celery -A celery_app worker --loglevel=info --pool=solo
```

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Main application |
| API | http://localhost:8000 | Backend API |
| API Docs | http://localhost:8000/docs | Swagger UI |
| MinIO Console | http://localhost:9001 | S3 Storage (minioadmin/minioadmin) |
| Qdrant Dashboard | http://localhost:6333/dashboard | Vector DB |

## Test Account
- Email: test@actorhub.ai
- Password: password123

## Stopping Services

```bash
# Stop Docker services
docker-compose down

# Or to also remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Troubleshooting

### API won't start
1. Check if venv is activated: `.\venv\Scripts\activate`
2. Check if Docker is running: `docker ps`
3. Check port 8000 is free: `netstat -ano | findstr :8000`

### Frontend won't start
1. Install dependencies: `npm install`
2. Check port 3000 is free: `netstat -ano | findstr :3000`

### Database errors
1. Check PostgreSQL is running: `docker ps | grep postgres`
2. Reset database: `docker-compose down -v && docker-compose up -d`

### Face Recognition not working
InsightFace is configured for CPU mode. Models are at:
`C:\Users\<username>\.insightface\models\buffalo_l\`

## Environment Files

- API: `apps/api/.env`
- Frontend: `apps/web/.env.local`
- Worker: Uses same env as API
