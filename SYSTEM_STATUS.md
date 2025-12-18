# ActorHub.ai - System Status Report
**Last Updated:** 2025-12-17 (Updated with 301 profiles)
**Version:** 1.0.0

---

## Quick Start (After Restart)

```bash
# 1. Start Docker containers
docker-compose up -d

# 2. Start Backend API
cd apps/api
..\..\..\venv\Scripts\activate  # or: source venv/bin/activate (Linux/Mac)
uvicorn app.main:app --reload --port 8000

# 3. Start Frontend
cd apps/web
npm run dev
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ActorHub.ai                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │   Frontend   │────▶│   Backend    │────▶│   Database   │     │
│  │   Next.js    │     │   FastAPI    │     │  PostgreSQL  │     │
│  │  Port 3000   │     │  Port 8000   │     │  Port 5433   │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│         │                    │                    │              │
│         │                    ▼                    │              │
│         │             ┌──────────────┐            │              │
│         │             │    Redis     │            │              │
│         │             │  Port 6380   │            │              │
│         │             └──────────────┘            │              │
│         │                    │                                   │
│         ▼                    ▼                                   │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     │
│  │    MinIO     │     │   Qdrant     │     │  InsightFace │     │
│  │  Port 9000   │     │  Port 6333   │     │  (In-Process)│     │
│  │  (Storage)   │     │  (Vectors)   │     │  buffalo_l   │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Service Status & Ports

| Service      | Port  | Internal Port | Status  | Purpose                    |
|--------------|-------|---------------|---------|----------------------------|
| PostgreSQL   | 5433  | 5432          | Healthy | Main database              |
| Redis        | 6380  | 6379          | Healthy | Caching & sessions         |
| Qdrant       | 6333  | 6333          | Running | Face embedding vectors     |
| MinIO        | 9000  | 9000          | Healthy | S3-compatible file storage |
| MinIO Console| 9001  | 9001          | Running | MinIO admin UI             |
| Backend API  | 8000  | -             | Manual  | FastAPI application        |
| Frontend     | 3000  | -             | Manual  | Next.js application        |

**Note:** Backend and Frontend require manual startup (not in Docker)

---

## Configuration Files

### Backend (`apps/api/.env`)
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/actorhub
REDIS_URL=redis://localhost:6380
HOST=0.0.0.0
PORT=8000
DEBUG=true
```

### Frontend (`apps/web/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA=false
```

**IMPORTANT:** `NEXT_PUBLIC_USE_MOCK_DATA=false` ensures frontend uses REAL backend data!

---

## Database Schema

### Tables (PostgreSQL)
| Table          | Purpose                              |
|----------------|--------------------------------------|
| users          | User accounts                        |
| identities     | Actor/model identity registrations   |
| actor_packs    | Packaged actor assets                |
| licenses       | Usage licenses for identities        |
| listings       | Marketplace listings                 |
| usage_logs     | API usage tracking                   |
| api_keys       | Developer API keys                   |

### Extensions
- `pgvector` - Vector similarity search (installed)
- `uuid-ossp` - UUID generation

### Current Data (Seeded 2025-12-17)
| Category    | Profiles | Featured |
|-------------|----------|----------|
| Actor       | 51       | ~5       |
| Model       | 50       | ~5       |
| Influencer  | 50       | ~5       |
| Character   | 50       | ~5       |
| Presenter   | 50       | ~5       |
| Voice       | 50       | ~5       |
| **TOTAL**   | **301**  | **~30**  |

### Vector Storage (Qdrant)
- Collection: `face_embeddings`
- Dimension: 512 (InsightFace buffalo_l)
- Distance: Cosine

---

## API Endpoints

### Health & Status
- `GET /health` - System health check
- `GET /api/v1/health` - API health with features

### Authentication
- `POST /api/v1/users/register` - User registration
- `POST /api/v1/users/login` - Login (returns JWT)
- `POST /api/v1/users/refresh` - Token refresh
- `GET /api/v1/users/me` - Current user info

### Marketplace
- `GET /api/v1/marketplace/listings` - All listings
- `GET /api/v1/marketplace/listings/{id}` - Single listing
- `GET /api/v1/marketplace/categories` - Categories list
- `GET /api/v1/marketplace/search` - Search listings

### Identity
- `GET /api/v1/identity/mine` - User's identities
- `POST /api/v1/identity/register` - Register new identity
- `POST /api/v1/identity/verify` - Verify face match

---

## Features Status

| Feature           | Status      | Notes                           |
|-------------------|-------------|---------------------------------|
| User Auth (JWT)   | ✅ Working  | Access + Refresh tokens         |
| Marketplace       | ✅ Working  | Listings from real database     |
| Face Recognition  | ✅ Working  | InsightFace buffalo_l model     |
| Vector Search     | ✅ Working  | Qdrant with 512-dim embeddings  |
| File Storage      | ✅ Working  | MinIO S3-compatible             |
| Voice Cloning     | ⏳ Planned  | Feature flag enabled            |
| Blockchain        | ❌ Disabled | Feature flag disabled           |

---

## Integration Test Results (2025-12-17)

```
[1/6] Backend API Health        ✅ PASSED
[2/6] Frontend Availability     ✅ PASSED (port 3001)
[3/6] Frontend API Proxy        ✅ PASSED
[4/6] Authentication Flow       ✅ PASSED
[5/6] Marketplace Real Data     ✅ PASSED (1 real listing)
[6/6] Database Connection       ✅ PASSED (6 categories)
```

**All systems connected and working!**

---

## Directory Structure

```
C:\ActorHub.ai 1.1\
├── apps/
│   ├── api/                 # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/v1/      # API routes
│   │   │   ├── core/        # Config, security, database
│   │   │   ├── models/      # SQLAlchemy models
│   │   │   ├── schemas/     # Pydantic schemas
│   │   │   └── services/    # Business logic
│   │   ├── .env             # Backend config
│   │   └── requirements.txt
│   │
│   ├── web/                 # Next.js Frontend
│   │   ├── src/
│   │   │   ├── app/         # Pages (App Router)
│   │   │   ├── components/  # React components
│   │   │   ├── lib/         # API client, utils
│   │   │   └── store/       # Zustand stores
│   │   ├── .env.local       # Frontend config
│   │   └── package.json
│   │
│   ├── worker/              # Celery workers (background tasks)
│   └── studio/              # Actor studio (planned)
│
├── tests/
│   ├── integration/         # Integration tests
│   │   ├── test_database.py
│   │   ├── test_auth.py
│   │   ├── test_identity.py
│   │   ├── test_face_recognition.py
│   │   ├── test_qdrant.py
│   │   └── test_end_to_end.py
│   └── unit/
│
├── docker-compose.yml       # Docker services
├── venv/                    # Python virtual environment
└── SYSTEM_STATUS.md         # This file
```

---

## Running Integration Tests

```bash
cd "C:\ActorHub.ai 1.1"

# All tests
python tests/integration/test_end_to_end.py
python tests/integration/test_database.py
python tests/integration/test_auth.py
python tests/integration/test_qdrant.py
python tests/integration/test_face_recognition.py
python tests/integration/test_identity.py
```

---

## Common Issues & Solutions

### 1. Port Already in Use
```bash
# Find process using port
netstat -ano | findstr :8000
# Kill by PID
taskkill /PID <pid> /F
```

### 2. Docker Containers Not Starting
```bash
docker-compose down
docker-compose up -d
docker ps  # Verify all healthy
```

### 3. Database Connection Failed
- Check PostgreSQL container: `docker logs actorhub-postgres`
- Verify port 5433 is accessible
- Check DATABASE_URL in `apps/api/.env`

### 4. Frontend Shows Mock Data
- Verify `apps/web/.env.local` has `NEXT_PUBLIC_USE_MOCK_DATA=false`
- Restart Next.js server after changing env

### 5. Face Recognition Not Working
- InsightFace downloads models on first run (~500MB)
- Check `C:\Users\<user>\.insightface\models\buffalo_l`

---

## Credentials (Development Only!)

| Service    | Username | Password   | URL                      |
|------------|----------|------------|--------------------------|
| PostgreSQL | postgres | postgres   | localhost:5433           |
| MinIO      | minioadmin| minioadmin| http://localhost:9001    |
| Redis      | -        | -          | localhost:6380           |
| Qdrant     | -        | -          | http://localhost:6333    |

---

## Recent Updates (2025-12-17)

1. ✅ Fixed admin page mock data flag (now uses env variable)
2. ✅ Created `.env.local` for frontend with `USE_MOCK_DATA=false`
3. ✅ Verified frontend-to-backend connectivity
4. ✅ All integration tests passing
5. ✅ Real data flowing from database to frontend

---

## Next Steps (Roadmap)

- [ ] Implement voice cloning service
- [ ] Add Celery worker for async tasks
- [ ] Create actor studio interface
- [ ] Add payment integration
- [ ] Implement blockchain verification (optional)

---

**Report Generated By:** Claude Code Integration Test Suite
