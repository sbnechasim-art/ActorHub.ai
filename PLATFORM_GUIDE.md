# ActorHub.ai - Platform Guide

## Quick Start

### Option 1: One-Click Launch (Recommended)

**Double-click:** `start-platform.bat`

Or from terminal:
```cmd
cd "C:\ActorHub.ai 1.1"
start-platform.bat
```

This script automatically:
1. Starts Docker containers (PostgreSQL, Redis, MinIO, Qdrant)
2. Starts Cloudflare Tunnel for MinIO public access
3. Starts Celery worker for background tasks
4. Starts API server (port 8000)
5. Starts Web frontend (port 3000)
6. Updates `.env` with tunnel URL

### Stop All Services
**Double-click:** `stop-platform.bat`

Or:
```cmd
cd "C:\ActorHub.ai 1.1"
stop-platform.bat
```

### Restart API Only
```cmd
cd "C:\ActorHub.ai 1.1"
restart-api.bat
```

---

### Option 2: Manual Start (Step by Step)

#### Step 1: Start Docker Services
```cmd
cd "C:\ActorHub.ai 1.1"
docker-compose up -d
```
Wait ~30 seconds for PostgreSQL, Redis, Qdrant, and MinIO to start.

#### Step 2: Start Cloudflare Tunnel
```cmd
cloudflared tunnel --url http://localhost:9000
```
Copy the `*.trycloudflare.com` URL and update `apps/api/.env`:
```
S3_PUBLIC_URL=https://YOUR-URL.trycloudflare.com
```

#### Step 3: Start API Server
Open a **new Command Prompt**:
```cmd
cd "C:\ActorHub.ai 1.1\apps\api"
.venv\Scripts\activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Wait for "Application startup complete"

#### Step 4: Start Celery Worker
Open a **new Command Prompt**:
```cmd
cd "C:\ActorHub.ai 1.1\apps\worker"
..\api\.venv\Scripts\activate
celery -A celery_app worker --loglevel=info --pool=solo -Q training,face,notifications,cleanup,payouts
```

#### Step 5: Start Web Frontend
Open a **new Command Prompt**:
```cmd
cd "C:\ActorHub.ai 1.1\apps\web"
npm run dev
```
Wait for "Ready in X.Xs"

---

## Access URLs

| Service | URL |
|---------|-----|
| **Web App** | http://localhost:3000 |
| **Admin Dashboard** | http://localhost:3000/admin |
| **API Docs** | http://localhost:8000/docs |
| **API Health** | http://localhost:8000/api/v1/health |

---

## Login Credentials

### Admin Account (Full Access)
- **Email:** sbnechasim@gmail.com
- **Password:** TT7589TT
- **Role:** ADMIN
- **Tier:** ENTERPRISE

### Test Account
- **Email:** test@actorhub.ai
- **Password:** password123
- **Role:** CREATOR
- **Tier:** PRO

---

## Admin Dashboard Features

Access: http://localhost:3000/admin

1. **Users Management** - View/edit all users, change roles and tiers
2. **Analytics** - Platform-wide statistics
3. **Audit Logs** - Track all system activities
4. **Webhooks** - Monitor Stripe/external webhooks
5. **Payouts** - Approve creator payouts

---

## Troubleshooting

### Port Already in Use
```cmd
netstat -ano | findstr :8000
taskkill /F /PID <PID_NUMBER>
```

### Database Connection Issues
Make sure Docker is running:
```cmd
docker-compose ps
```

### Face Recognition Not Detecting Faces
The fix has been applied (det_thresh=0.3). Restart the API server.

---

## Services Architecture

```
Docker Containers (docker-compose):
  - PostgreSQL (port 5433) - Database
  - Redis (port 6380) - Cache & Celery broker
  - Qdrant (port 6333) - Vector DB for face embeddings
  - MinIO (port 9000/9001) - S3-compatible storage

Cloudflare Tunnel:
  - Exposes MinIO to internet (*.trycloudflare.com)
  - Required for Replicate LoRA training

Python Services:
  - FastAPI (port 8000) - Main API
  - Celery Worker - Background tasks (training, notifications)

Node.js Frontend (Next.js):
  - Web app on port 3000
```

## Batch Scripts

| Script | Description |
|--------|-------------|
| `start-platform.bat` | Start all services (Docker, Tunnel, Celery, API, Web) |
| `stop-platform.bat` | Stop all services |
| `restart-api.bat` | Quick API restart only |
