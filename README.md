# 💜 Kindred — Dating App Backend

> *"Designed for people who know what they want — and what they don't."*
> Targeting middle-aged adults seeking meaningful connections after marriage/divorce.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (Python 3.11) |
| Database | PostgreSQL 15 + SQLAlchemy (async) |
| Cache | Redis 7 |
| Auth | JWT + Google OAuth2 |
| Photos | Cloudinary |
| Payments | Stripe |
| Email | SendGrid |
| Hosting | Railway.app |

---

## Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Node.js (for frontend only)

### 1 — Clone and set up environment

```bash
git clone https://github.com/yourname/kindred.git
cd kindred/backend

# Copy env template
cp .env.example .env
# Edit .env and fill in your API keys
```

### 2 — Start database and Redis

```bash
# From project root
docker-compose up db redis -d
```

### 3 — Install Python dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4 — Run database migrations

```bash
alembic upgrade head
```

### 5 — Start the API server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 6 — Open API docs

```
http://localhost:8000/docs        ← Swagger UI (dev only)
http://localhost:8000/redoc       ← ReDoc
http://localhost:8000/health      ← Health check
```

---

## Run with Docker (Full Stack)

```bash
# From project root — starts API + PostgreSQL + Redis
docker-compose up --build
```

---

## Deploy to Railway

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create project
railway init

# Add PostgreSQL and Redis
railway add postgresql
railway add redis

# Set environment variables
railway variables set SECRET_KEY=your_secret \
  STRIPE_SECRET_KEY=sk_live_xxx \
  SENDGRID_API_KEY=SG.xxx \
  CLOUDINARY_CLOUD_NAME=xxx \
  # ... (all variables from .env.example)

# Deploy
railway up
```

---

## API Endpoints Summary

```
POST   /api/v1/auth/register          Register new account
POST   /api/v1/auth/login             Login
POST   /api/v1/auth/refresh           Refresh token
POST   /api/v1/auth/google            Google OAuth
POST   /api/v1/auth/verify-email      Email verification
POST   /api/v1/auth/forgot-password   Password reset request
POST   /api/v1/auth/reset-password    Password reset confirm

GET    /api/v1/profiles/me            My profile
POST   /api/v1/profiles/me            Create profile
PUT    /api/v1/profiles/me            Update profile
DELETE /api/v1/profiles/me            Delete account (GDPR)
GET    /api/v1/profiles/discover/feed Discovery feed
GET    /api/v1/profiles/{id}          View a profile
POST   /api/v1/profiles/photos        Upload photo
DELETE /api/v1/profiles/photos/{id}   Delete photo

POST   /api/v1/matches/swipe          Swipe like/pass/superlike
GET    /api/v1/matches                My matches list
DELETE /api/v1/matches/{id}           Unmatch

GET    /api/v1/messages/{match_id}    Get conversation
POST   /api/v1/messages/{match_id}    Send message
WS     /ws/chat/{match_id}            Real-time chat

GET    /api/v1/subscriptions/plans    Available plans
GET    /api/v1/subscriptions/me       My subscription
POST   /api/v1/subscriptions/checkout Stripe checkout
POST   /api/v1/subscriptions/webhook  Stripe webhook

POST   /api/v1/safety/report          Report user
POST   /api/v1/safety/block           Block user
DELETE /api/v1/safety/block/{id}      Unblock user
```

---

## Subscription Tiers

| Feature | Free | Kindred $14.99 | Kindred Plus $29.99 |
|---|---|---|---|
| Daily swipes | 10 | Unlimited | Unlimited |
| Messages/match | 3 | Unlimited | Unlimited |
| Photos | 2 | 6 | 6 |
| Advanced filters | ❌ | ✅ | ✅ |
| See who liked you | ❌ | ❌ | ✅ |
| Boosts/month | 0 | 1 | 3 |
| Priority discovery | ❌ | ❌ | ✅ |

---

## Run Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app entry point
├── requirements.txt         # Python dependencies
├── alembic.ini              # DB migration config
├── railway.json             # Railway deployment
├── Dockerfile               # Production container
├── .env.example             # Environment template
├── app/
│   ├── config.py            # Settings
│   ├── database.py          # DB connection
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   ├── middleware/          # Auth, rate limiting, security
│   ├── websocket/           # Real-time chat
│   └── utils/               # Helpers, validators, security
├── migrations/              # Alembic migration files
└── tests/                   # pytest test suite
```

---

## Next Steps (Frontend)

The frontend lives in `/frontend/` and connects to this API.
See `frontend/README.md` for setup instructions.

Key frontend files to be generated:
- `index.html` — App shell
- `js/api.js` — API client
- `js/auth.js` — Auth state management
- `js/discover.js` — Swipe UI
- `js/messages.js` — Chat UI

---

*Built with FastAPI · PostgreSQL · Redis · Stripe · Railway*
*Kindred v1.0 — Phase 1 Foundation*
