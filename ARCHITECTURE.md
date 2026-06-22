# 💜 Kindred — Complete System Architecture
## "Designed for people who know what they want — and what they don't."
### Target: Middle-aged adults | Post-marriage | Meaningful connections

---

## 1. PROJECT OVERVIEW

| Property | Value |
|---|---|
| App Name | Kindred |
| Target Demographic | Ages 35–65, post-marriage/divorce |
| Platform | Web (mobile-first) + PWA |
| Backend | Python (FastAPI) |
| Frontend | HTML/CSS/JS (Kindred UI) |
| Database | PostgreSQL + Redis |
| Hosting | Railway.app |
| Payments | Stripe |
| Storage | Cloudinary |
| Auth | JWT + Google OAuth2 |

---

## 2. SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                            │
│                                                                 │
│   ┌─────────────────────────────────────────────────────┐      │
│   │              Kindred Web App (PWA)                  │      │
│   │   HTML · CSS · Vanilla JS · Service Worker          │      │
│   │                                                     │      │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │      │
│   │  │  Auth    │ │ Discover │ │ Messages │ │Profile│ │      │
│   │  │  Screen  │ │  Swipe   │ │   Chat   │ │Editor │ │      │
│   │  └──────────┘ └──────────┘ └──────────┘ └───────┘ │      │
│   │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐ │      │
│   │  │ Matches  │ │ Filters  │ │Subscribe │ │Settings│ │      │
│   │  └──────────┘ └──────────┘ └──────────┘ └───────┘ │      │
│   └─────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                    HTTPS / WSS (TLS)
                              │
┌─────────────────────────────────────────────────────────────────┐
│                         API GATEWAY                             │
│              FastAPI (Python 3.11+) on Railway                  │
│                                                                 │
│   /api/v1/auth          /api/v1/profiles                        │
│   /api/v1/matches       /api/v1/messages                        │
│   /api/v1/subscriptions /api/v1/admin                           │
│   ws://kindred.app/ws   (WebSocket — real-time chat)            │
└─────────────────────────────────────────────────────────────────┘
          │               │               │               │
    ┌─────┴──┐      ┌─────┴──┐     ┌──────┴─┐     ┌──────┴─┐
    │  Auth  │      │Business│     │Realtime│     │External│
    │Service │      │ Logic  │     │Service │     │Services│
    └─────┬──┘      └─────┬──┘     └──────┬─┘     └──────┬─┘
          │               │               │               │
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  PostgreSQL  │  │    Redis     │  │      Cloudinary       │ │
│  │              │  │              │  │                       │ │
│  │ · users      │  │ · sessions   │  │ · profile photos      │ │
│  │ · profiles   │  │ · match queue│  │ · verification docs   │ │
│  │ · matches    │  │ · rate limits│  │ · CDN delivery        │ │
│  │ · messages   │  │ · online     │  │                       │ │
│  │ · swipes     │  │   presence   │  └───────────────────────┘ │
│  │ · subs       │  │ · pub/sub    │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                               │
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                            │
│                                                                 │
│  ┌───────────┐  ┌───────────┐  ┌──────────┐  ┌─────────────┐  │
│  │  Google   │  │  Stripe   │  │ SendGrid │  │   Twilio    │  │
│  │  OAuth2   │  │ Payments  │  │  Emails  │  │ SMS Verify  │  │
│  └───────────┘  └───────────┘  └──────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. FOLDER STRUCTURE

```
kindred/
│
├── backend/                          # FastAPI Python backend
│   ├── main.py                       # App entry point
│   ├── requirements.txt              # Python dependencies
│   ├── .env                          # Environment variables (never commit)
│   ├── .env.example                  # Template for env variables
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                 # Settings & config management
│   │   ├── database.py               # DB connection & session
│   │   │
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # User & auth model
│   │   │   ├── profile.py            # Dating profile model
│   │   │   ├── match.py              # Match & swipe model
│   │   │   ├── message.py            # Chat message model
│   │   │   └── subscription.py       # Subscription model
│   │   │
│   │   ├── schemas/                  # Pydantic validation schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # Login/register schemas
│   │   │   ├── profile.py            # Profile schemas
│   │   │   ├── match.py              # Match schemas
│   │   │   ├── message.py            # Message schemas
│   │   │   └── subscription.py       # Subscription schemas
│   │   │
│   │   ├── routers/                  # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py               # /api/v1/auth/*
│   │   │   ├── profiles.py           # /api/v1/profiles/*
│   │   │   ├── matches.py            # /api/v1/matches/*
│   │   │   ├── messages.py           # /api/v1/messages/*
│   │   │   ├── subscriptions.py      # /api/v1/subscriptions/*
│   │   │   └── admin.py              # /api/v1/admin/*
│   │   │
│   │   ├── services/                 # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py       # JWT, OAuth, sessions
│   │   │   ├── profile_service.py    # Profile CRUD
│   │   │   ├── matching_service.py   # Matching algorithm
│   │   │   ├── chat_service.py       # WebSocket chat
│   │   │   ├── subscription_service.py # Stripe integration
│   │   │   ├── photo_service.py      # Cloudinary uploads
│   │   │   ├── email_service.py      # SendGrid emails
│   │   │   └── moderation_service.py # Report/block logic
│   │   │
│   │   ├── middleware/               # FastAPI middleware
│   │   │   ├── __init__.py
│   │   │   ├── auth_middleware.py    # JWT verification
│   │   │   ├── rate_limiter.py       # Redis-based rate limiting
│   │   │   └── security.py          # CORS, headers, HTTPS
│   │   │
│   │   ├── websocket/                # Real-time chat
│   │   │   ├── __init__.py
│   │   │   ├── manager.py            # Connection manager
│   │   │   └── handlers.py           # Message handlers
│   │   │
│   │   └── utils/                   # Helpers & utilities
│   │       ├── __init__.py
│   │       ├── security.py           # Password hashing
│   │       ├── validators.py         # Input validation
│   │       └── helpers.py            # General helpers
│   │
│   ├── migrations/                   # Alembic DB migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   │
│   └── tests/                        # Pytest test suite
│       ├── __init__.py
│       ├── test_auth.py
│       ├── test_profiles.py
│       ├── test_matching.py
│       └── test_subscriptions.py
│
├── frontend/                         # Web frontend
│   ├── index.html                    # App shell
│   ├── manifest.json                 # PWA manifest
│   ├── service-worker.js             # PWA offline support
│   │
│   ├── css/
│   │   ├── main.css                  # Global styles & variables
│   │   ├── auth.css                  # Login/register screens
│   │   ├── discover.css              # Swipe card UI
│   │   ├── messages.css              # Chat UI
│   │   ├── profile.css               # Profile editor
│   │   └── subscription.css          # Pricing/upgrade UI
│   │
│   ├── js/
│   │   ├── app.js                    # App init & routing
│   │   ├── api.js                    # API client (fetch wrapper)
│   │   ├── auth.js                   # Auth state management
│   │   ├── discover.js               # Swipe logic
│   │   ├── messages.js               # Chat + WebSocket client
│   │   ├── profile.js                # Profile management
│   │   └── subscription.js           # Stripe checkout
│   │
│   └── assets/
│       ├── icons/                    # PWA icons (various sizes)
│       ├── images/                   # Static images
│       └── fonts/                    # Custom fonts
│
├── docker-compose.yml                # Local dev environment
├── Dockerfile                        # Production container
├── railway.json                      # Railway deployment config
├── alembic.ini                       # DB migration config
└── README.md                         # Setup instructions
```

---

## 4. DATABASE SCHEMA

```sql
-- ══════════════════════════════════════════
-- USERS & AUTHENTICATION
-- ══════════════════════════════════════════

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    phone           VARCHAR(20) UNIQUE,
    password_hash   VARCHAR(255),           -- NULL if OAuth only
    google_id       VARCHAR(255) UNIQUE,    -- Google OAuth
    is_verified     BOOLEAN DEFAULT FALSE,
    is_active       BOOLEAN DEFAULT TRUE,
    is_banned       BOOLEAN DEFAULT FALSE,
    role            VARCHAR(20) DEFAULT 'user',  -- user/admin/moderator
    created_at      TIMESTAMP DEFAULT NOW(),
    last_login      TIMESTAMP,
    deleted_at      TIMESTAMP               -- soft delete
);

-- ══════════════════════════════════════════
-- DATING PROFILES
-- ══════════════════════════════════════════

CREATE TABLE profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    first_name      VARCHAR(50) NOT NULL,
    age             INTEGER NOT NULL CHECK (age >= 30 AND age <= 80),
    gender          VARCHAR(20) NOT NULL,
    seeking          VARCHAR(20) NOT NULL,
    location_city   VARCHAR(100),
    location_country VARCHAR(100),
    latitude        DECIMAL(9,6),
    longitude       DECIMAL(9,6),
    bio             TEXT CHECK (char_length(bio) <= 500),
    occupation      VARCHAR(100),
    education       VARCHAR(100),
    height_cm       INTEGER,
    has_children    VARCHAR(20),            -- yes/no/sometimes
    wants_children  VARCHAR(20),
    relationship_goal VARCHAR(50),         -- serious/casual/friendship
    marital_history VARCHAR(50),           -- divorced/widowed/never-married
    religion        VARCHAR(50),
    drinking        VARCHAR(30),
    smoking         VARCHAR(30),
    interests       TEXT[],                -- array of interest tags
    languages       TEXT[],
    profile_complete BOOLEAN DEFAULT FALSE,
    is_visible      BOOLEAN DEFAULT TRUE,
    last_active     TIMESTAMP DEFAULT NOW(),
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);

-- ══════════════════════════════════════════
-- PROFILE PHOTOS
-- ══════════════════════════════════════════

CREATE TABLE photos (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id      UUID REFERENCES profiles(id) ON DELETE CASCADE,
    cloudinary_id   VARCHAR(255) NOT NULL,
    url             TEXT NOT NULL,
    thumbnail_url   TEXT,
    is_primary      BOOLEAN DEFAULT FALSE,
    is_verified     BOOLEAN DEFAULT FALSE,
    sort_order      INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- ══════════════════════════════════════════
-- SWIPES & MATCHES
-- ══════════════════════════════════════════

CREATE TABLE swipes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    swiper_id       UUID REFERENCES profiles(id) ON DELETE CASCADE,
    swiped_id       UUID REFERENCES profiles(id) ON DELETE CASCADE,
    direction       VARCHAR(10) NOT NULL,   -- like/pass/superlike
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(swiper_id, swiped_id)
);

CREATE TABLE matches (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_1_id    UUID REFERENCES profiles(id) ON DELETE CASCADE,
    profile_2_id    UUID REFERENCES profiles(id) ON DELETE CASCADE,
    matched_at      TIMESTAMP DEFAULT NOW(),
    is_active       BOOLEAN DEFAULT TRUE,
    last_message_at TIMESTAMP,
    UNIQUE(profile_1_id, profile_2_id)
);

-- ══════════════════════════════════════════
-- MESSAGES
-- ══════════════════════════════════════════

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        UUID REFERENCES matches(id) ON DELETE CASCADE,
    sender_id       UUID REFERENCES profiles(id) ON DELETE CASCADE,
    content         TEXT NOT NULL CHECK (char_length(content) <= 1000),
    message_type    VARCHAR(20) DEFAULT 'text',  -- text/image/emoji
    is_read         BOOLEAN DEFAULT FALSE,
    read_at         TIMESTAMP,
    created_at      TIMESTAMP DEFAULT NOW(),
    deleted_at      TIMESTAMP               -- soft delete
);

-- ══════════════════════════════════════════
-- SUBSCRIPTIONS
-- ══════════════════════════════════════════

CREATE TABLE subscriptions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    stripe_customer_id  VARCHAR(255) UNIQUE,
    stripe_sub_id       VARCHAR(255) UNIQUE,
    plan                VARCHAR(20) DEFAULT 'free',  -- free/kindred/kindred_plus
    status              VARCHAR(20) DEFAULT 'active',
    current_period_start TIMESTAMP,
    current_period_end  TIMESTAMP,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT NOW(),
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- ══════════════════════════════════════════
-- SAFETY & MODERATION
-- ══════════════════════════════════════════

CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    reporter_id     UUID REFERENCES users(id),
    reported_id     UUID REFERENCES users(id),
    reason          VARCHAR(100) NOT NULL,
    description     TEXT,
    status          VARCHAR(20) DEFAULT 'pending',
    reviewed_by     UUID REFERENCES users(id),
    created_at      TIMESTAMP DEFAULT NOW()
);

CREATE TABLE blocks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    blocker_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    blocked_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE(blocker_id, blocked_id)
);

-- ══════════════════════════════════════════
-- DAILY LIMITS (for free tier)
-- ══════════════════════════════════════════

CREATE TABLE daily_limits (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    date            DATE DEFAULT CURRENT_DATE,
    swipes_used     INTEGER DEFAULT 0,
    messages_sent   INTEGER DEFAULT 0,
    superlikes_used INTEGER DEFAULT 0,
    UNIQUE(user_id, date)
);
```

---

## 5. API ENDPOINTS

```
AUTH MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST   /api/v1/auth/register          Register with email/password
POST   /api/v1/auth/login             Login → returns JWT tokens
POST   /api/v1/auth/logout            Invalidate token
POST   /api/v1/auth/refresh           Refresh access token
POST   /api/v1/auth/google            Google OAuth login
POST   /api/v1/auth/forgot-password   Send reset email
POST   /api/v1/auth/reset-password    Reset with token
POST   /api/v1/auth/verify-email      Email verification
POST   /api/v1/auth/verify-phone      SMS verification (Twilio)

PROFILES MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /api/v1/profiles/me            Get own profile
PUT    /api/v1/profiles/me            Update own profile
DELETE /api/v1/profiles/me            Delete account (GDPR)
GET    /api/v1/profiles/{id}          Get profile by ID
POST   /api/v1/profiles/photos        Upload photo (Cloudinary)
DELETE /api/v1/profiles/photos/{id}   Delete photo
PUT    /api/v1/profiles/photos/reorder Reorder photos
GET    /api/v1/profiles/me/visibility Toggle profile visibility

DISCOVER MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /api/v1/discover               Get candidate profiles (paginated)
GET    /api/v1/discover/filters       Get filter options
POST   /api/v1/discover/filters       Save filter preferences

MATCHES MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST   /api/v1/matches/swipe          Submit swipe (like/pass/superlike)
GET    /api/v1/matches                Get all matches
GET    /api/v1/matches/{id}           Get match detail
DELETE /api/v1/matches/{id}           Unmatch
GET    /api/v1/matches/liked-me       Who liked me (Premium only)

MESSAGES MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /api/v1/messages               Get all conversations
GET    /api/v1/messages/{match_id}    Get messages in a match
POST   /api/v1/messages/{match_id}    Send message
DELETE /api/v1/messages/{id}          Delete message
PUT    /api/v1/messages/{match_id}/read  Mark as read
WS     /ws/{match_id}                 WebSocket — real-time chat

SUBSCRIPTIONS MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /api/v1/subscriptions/plans    Get available plans
GET    /api/v1/subscriptions/me       Get current subscription
POST   /api/v1/subscriptions/checkout Create Stripe checkout session
POST   /api/v1/subscriptions/portal   Stripe customer portal
POST   /api/v1/subscriptions/webhook  Stripe webhook handler
DELETE /api/v1/subscriptions/cancel   Cancel subscription

SAFETY MODULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST   /api/v1/safety/report          Report a user
POST   /api/v1/safety/block           Block a user
DELETE /api/v1/safety/block/{id}      Unblock a user
GET    /api/v1/safety/blocked         Get blocked users list

ADMIN MODULE (admin role only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GET    /api/v1/admin/users            List all users
PUT    /api/v1/admin/users/{id}/ban   Ban a user
GET    /api/v1/admin/reports          List pending reports
PUT    /api/v1/admin/reports/{id}     Resolve a report
GET    /api/v1/admin/stats            App analytics
```

---

## 6. SUBSCRIPTION PLANS

```
┌─────────────────────────────────────────────────────────────────┐
│                    KINDRED SUBSCRIPTION TIERS                   │
├───────────────────┬─────────────────┬───────────────────────────┤
│     FREE          │   KINDRED        │     KINDRED PLUS          │
│     $0/month      │   $14.99/month   │     $29.99/month          │
├───────────────────┼─────────────────┼───────────────────────────┤
│ 10 swipes/day     │ Unlimited swipes│ Everything in Kindred      │
│ 3 messages/match  │ Unlimited msgs  │ See who liked you          │
│ Basic filters     │ Advanced filters│ 3 boosts/month             │
│ 2 photos max      │ 6 photos        │ 6 photos                   │
│                   │ Read receipts   │ Priority in discovery      │
│                   │ Undo last swipe │ Profile badge              │
│                   │                 │ Dedicated support          │
└───────────────────┴─────────────────┴───────────────────────────┘
```

---

## 7. MATCHING ALGORITHM

```python
"""
Kindred Compatibility Score — weighted factors:

Base Score (location + age):
  - Distance weight:     25%
  - Age range match:     20%

Compatibility Score:
  - Relationship goal:   20%  (must align — serious vs casual)
  - Life stage:          15%  (has/wants children match)
  - Interests overlap:   10%
  - Education level:     5%
  - Lifestyle match:      5%  (drinking/smoking)

Total:                   100%

Minimum score to show:   40%
Premium boost:           +15% visibility multiplier
Superlike:               Always shown to recipient
"""
```

---

## 8. SECURITY CHECKLIST

```
AUTHENTICATION
  ✅ Bcrypt password hashing (cost factor 12)
  ✅ JWT access tokens (15 min expiry)
  ✅ JWT refresh tokens (30 day expiry, stored in HttpOnly cookie)
  ✅ Google OAuth2 PKCE flow
  ✅ Email verification required before discovery
  ✅ Phone verification optional (Twilio)

API SECURITY
  ✅ HTTPS only (TLS 1.3)
  ✅ CORS — whitelist only known origins
  ✅ Rate limiting — Redis-based per IP + per user
  ✅ Input validation — Pydantic schemas on all endpoints
  ✅ SQL injection prevention — SQLAlchemy ORM only
  ✅ XSS prevention — Content-Security-Policy headers
  ✅ CSRF protection — SameSite cookie attribute

DATA PRIVACY (GDPR)
  ✅ Right to deletion — /profiles/me DELETE endpoint
  ✅ Data export — downloadable JSON of all user data
  ✅ Privacy policy & terms acceptance on register
  ✅ Minimal data collection principle
  ✅ Soft deletes — data retained 30 days then purged

PHOTO SAFETY
  ✅ Cloudinary content moderation (auto-detect explicit)
  ✅ File type validation (JPEG/PNG/WEBP only)
  ✅ Max file size: 5MB
  ✅ EXIF data stripped on upload
```

---

## 9. ENVIRONMENT VARIABLES

```bash
# .env.example — copy to .env and fill in values

# App
APP_NAME=Kindred
APP_ENV=development          # development / production
SECRET_KEY=                  # 64-char random string
DEBUG=True

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kindred
REDIS_URL=redis://localhost:6379/0

# Auth
JWT_SECRET=                  # 64-char random string
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Cloudinary
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_KINDRED_PRICE_ID=
STRIPE_KINDRED_PLUS_PRICE_ID=

# SendGrid
SENDGRID_API_KEY=
FROM_EMAIL=hello@kindred.app

# Twilio (optional SMS verification)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# Frontend
FRONTEND_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000,https://kindred.app
```

---

## 10. DEVELOPMENT PHASES

```
PHASE 1 — Foundation (Weeks 1–2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Project setup & folder structure
  ✦ Database models & migrations
  ✦ User authentication (email + Google OAuth)
  ✦ JWT token system
  ✦ Basic profile CRUD
  ✦ Photo upload via Cloudinary
  ✦ Deploy skeleton to Railway

PHASE 2 — Core Features (Weeks 3–4)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Discovery engine (candidate filtering)
  ✦ Matching algorithm (compatibility score)
  ✦ Swipe system (like/pass/superlike)
  ✦ Match detection & notifications
  ✦ Real-time chat via WebSockets
  ✦ Frontend: Discover + Messages screens

PHASE 3 — Monetisation (Week 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Stripe subscription integration
  ✦ Free / Kindred / Kindred Plus tiers
  ✦ Feature gating middleware
  ✦ Daily limits enforcement
  ✦ Subscription management UI
  ✦ Stripe webhook handling

PHASE 4 — Trust & Safety (Week 6)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ Report & block system
  ✦ Photo moderation (Cloudinary AI)
  ✦ Email verification flow
  ✦ Rate limiting on all endpoints
  ✦ Admin dashboard
  ✦ GDPR data export & deletion

PHASE 5 — Polish & Launch (Week 7–8)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✦ PWA manifest + service worker
  ✦ Push notifications
  ✦ Performance optimisation
  ✦ Security audit
  ✦ Beta testing with real users
  ✦ Production deployment
```

---

## 11. RAILWAY DEPLOYMENT CONFIG

```json
// railway.json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

---

## 12. PYTHON DEPENDENCIES

```txt
# requirements.txt

# Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.25
asyncpg==0.29.0
alembic==1.13.1
psycopg2-binary==2.9.9

# Cache
redis==5.0.1
aioredis==2.0.1

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-oauth2==1.1.1
httpx==0.26.0

# Validation
pydantic==2.5.3
pydantic-settings==2.1.0
email-validator==2.1.0

# File uploads
cloudinary==1.38.0
pillow==10.2.0

# Payments
stripe==7.12.0

# Email
sendgrid==6.11.0

# SMS
twilio==8.12.0

# Utilities
python-dotenv==1.0.0
pytz==2024.1
slowapi==0.1.9      # Rate limiting

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
factory-boy==3.3.0
```

---

*Architecture Version 1.0 — Kindred Dating App*
*Target: Middle-aged adults seeking meaningful connections*
*Built with FastAPI · PostgreSQL · Redis · Stripe · Railway*
