# ActorHub.ai - דוח מצב מערכת
**עודכן לאחרונה:** 2025-12-17
**גרסה:** 1.0.0

---

## התחלה מהירה (אחרי הפעלה מחדש)

```bash
# 1. הפעלת Docker containers
docker-compose up -d

# 2. הפעלת Backend API
cd apps/api
..\..\..\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# 3. הפעלת Frontend
cd apps/web
npm run dev
```

---

## ארכיטקטורת המערכת

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
│  │  (אחסון)     │     │  (וקטורים)   │     │  buffalo_l   │     │
│  └──────────────┘     └──────────────┘     └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## סטטוס שירותים ופורטים

| שירות        | פורט  | פורט פנימי | סטטוס   | תפקיד                      |
|--------------|-------|------------|---------|----------------------------|
| PostgreSQL   | 5433  | 5432       | תקין    | בסיס נתונים ראשי           |
| Redis        | 6380  | 6379       | תקין    | קאשינג וסשנים              |
| Qdrant       | 6333  | 6333       | רץ      | וקטורים לזיהוי פנים        |
| MinIO        | 9000  | 9000       | תקין    | אחסון קבצים S3             |
| Backend API  | 8000  | -          | ידני    | FastAPI                    |
| Frontend     | 3000  | -          | ידני    | Next.js                    |

**הערה:** Backend ו-Frontend דורשים הפעלה ידנית (לא ב-Docker)

---

## קבצי קונפיגורציה

### Backend (`apps/api/.env`)
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/actorhub
REDIS_URL=redis://localhost:6380
PORT=8000
```

### Frontend (`apps/web/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCK_DATA=false
```

**חשוב:** `NEXT_PUBLIC_USE_MOCK_DATA=false` מבטיח שהפרונט משתמש בנתונים אמיתיים!

---

## סכמת בסיס הנתונים

### טבלאות (PostgreSQL)
| טבלה           | תפקיד                                |
|----------------|--------------------------------------|
| users          | חשבונות משתמשים                      |
| identities     | רישום זהויות שחקנים/מודלים           |
| actor_packs    | חבילות נכסי שחקנים                   |
| licenses       | רישיונות שימוש בזהויות               |
| listings       | פריטים ב-Marketplace                 |
| usage_logs     | מעקב שימוש ב-API                     |
| api_keys       | מפתחות API למפתחים                   |

### הרחבות
- `pgvector` - חיפוש דמיון וקטורי (מותקן)
- `uuid-ossp` - יצירת UUID

### אחסון וקטורים (Qdrant)
- Collection: `face_embeddings`
- מימד: 512 (InsightFace buffalo_l)
- מרחק: Cosine

---

## נקודות קצה API

### בריאות וסטטוס
- `GET /health` - בדיקת בריאות מערכת
- `GET /api/v1/health` - בריאות API עם פיצ'רים

### אימות משתמשים
- `POST /api/v1/users/register` - הרשמה
- `POST /api/v1/users/login` - התחברות (מחזיר JWT)
- `POST /api/v1/users/refresh` - רענון טוקן
- `GET /api/v1/users/me` - פרטי משתמש נוכחי

### שוק (Marketplace)
- `GET /api/v1/marketplace/listings` - כל הפריטים
- `GET /api/v1/marketplace/listings/{id}` - פריט בודד
- `GET /api/v1/marketplace/categories` - קטגוריות
- `GET /api/v1/marketplace/search` - חיפוש

### זהות (Identity)
- `GET /api/v1/identity/mine` - הזהויות שלי
- `POST /api/v1/identity/register` - רישום זהות חדשה
- `POST /api/v1/identity/verify` - אימות התאמת פנים

---

## סטטוס פיצ'רים

| פיצ'ר             | סטטוס      | הערות                           |
|-------------------|------------|--------------------------------|
| אימות JWT         | ✅ עובד    | Access + Refresh tokens         |
| Marketplace       | ✅ עובד    | נתונים מהדאטאבייס האמיתי        |
| זיהוי פנים        | ✅ עובד    | מודל InsightFace buffalo_l      |
| חיפוש וקטורי      | ✅ עובד    | Qdrant עם 512 מימדים            |
| אחסון קבצים       | ✅ עובד    | MinIO תואם S3                   |
| שיבוט קול         | ⏳ מתוכנן  | Feature flag מופעל              |
| בלוקצ'יין         | ❌ מכובה   | Feature flag מכובה              |

---

## תוצאות בדיקות אינטגרציה (2025-12-17)

```
[1/6] Backend API Health        ✅ עבר
[2/6] Frontend Availability     ✅ עבר (port 3001)
[3/6] Frontend API Proxy        ✅ עבר
[4/6] Authentication Flow       ✅ עבר
[5/6] Marketplace Real Data     ✅ עבר (1 פריט אמיתי)
[6/6] Database Connection       ✅ עבר (6 קטגוריות)
```

**כל המערכות מחוברות ועובדות!**

---

## מבנה תיקיות

```
C:\ActorHub.ai 1.1\
├── apps/
│   ├── api/                 # FastAPI Backend
│   │   ├── app/
│   │   │   ├── api/v1/      # נתיבי API
│   │   │   ├── core/        # קונפיג, אבטחה, DB
│   │   │   ├── models/      # מודלים SQLAlchemy
│   │   │   ├── schemas/     # סכמות Pydantic
│   │   │   └── services/    # לוגיקה עסקית
│   │   └── .env
│   │
│   ├── web/                 # Next.js Frontend
│   │   ├── src/
│   │   │   ├── app/         # דפים (App Router)
│   │   │   ├── components/  # קומפוננטות React
│   │   │   ├── lib/         # API client, utils
│   │   │   └── store/       # Zustand stores
│   │   └── .env.local
│   │
│   ├── worker/              # Celery workers
│   └── studio/              # Actor studio (מתוכנן)
│
├── tests/integration/       # בדיקות אינטגרציה
├── docker-compose.yml       # שירותי Docker
├── venv/                    # סביבת Python וירטואלית
├── SYSTEM_STATUS.md         # דוח באנגלית
└── SYSTEM_STATUS_HE.md      # דוח זה
```

---

## הרצת בדיקות אינטגרציה

```bash
cd "C:\ActorHub.ai 1.1"

# כל הבדיקות
python tests/integration/test_end_to_end.py
python tests/integration/test_database.py
python tests/integration/test_auth.py
python tests/integration/test_qdrant.py
python tests/integration/test_face_recognition.py
python tests/integration/test_identity.py
```

---

## בעיות נפוצות ופתרונות

### 1. פורט תפוס
```bash
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### 2. Docker לא עולה
```bash
docker-compose down
docker-compose up -d
docker ps
```

### 3. בעיית חיבור לדאטאבייס
- בדוק: `docker logs actorhub-postgres`
- ודא שפורט 5433 נגיש
- בדוק DATABASE_URL ב-`apps/api/.env`

### 4. הפרונט מציג Mock Data
- ודא ש-`apps/web/.env.local` מכיל `NEXT_PUBLIC_USE_MOCK_DATA=false`
- הפעל מחדש את Next.js

### 5. זיהוי פנים לא עובד
- InsightFace מוריד מודלים בהפעלה ראשונה (~500MB)
- בדוק: `C:\Users\<user>\.insightface\models\buffalo_l`

---

## פרטי התחברות (פיתוח בלבד!)

| שירות     | משתמש     | סיסמה     | כתובת                    |
|-----------|-----------|-----------|--------------------------|
| PostgreSQL| postgres  | postgres  | localhost:5433           |
| MinIO     | minioadmin| minioadmin| http://localhost:9001    |
| Redis     | -         | -         | localhost:6380           |
| Qdrant    | -         | -         | http://localhost:6333    |

---

## עדכונים אחרונים (2025-12-17)

1. ✅ תוקן דגל Mock Data בדף Admin (עכשיו משתמש ב-env variable)
2. ✅ נוצר `.env.local` לפרונט עם `USE_MOCK_DATA=false`
3. ✅ אומת חיבור Frontend-Backend
4. ✅ כל בדיקות האינטגרציה עוברות
5. ✅ נתונים אמיתיים זורמים מהדאטאבייס לפרונט

---

## שלבים הבאים (Roadmap)

- [ ] להטמיע שירות שיבוט קול
- [ ] להוסיף Celery worker למשימות רקע
- [ ] ליצור ממשק Actor Studio
- [ ] להוסיף אינטגרציית תשלומים
- [ ] להטמיע אימות בלוקצ'יין (אופציונלי)

---

**הדוח נוצר ע"י:** Claude Code Integration Test Suite
