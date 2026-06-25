#!/bin/bash
# ════════════════════════════════════════════════════════════
# Mellow — Local Mac Setup Script
# Supports both PostgreSQL (if available) and SQLite (fallback)
# Usage: bash local_setup.sh
# ════════════════════════════════════════════════════════════

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }
err()  { echo -e "${RED}✗ $1${NC}"; exit 1; }

echo ""
echo "🌿 Setting up Mellow locally..."
echo ""

# ── Check Python ──────────────────────────────────────────────
PYTHON=$(which python3 || which python)
$PYTHON --version | grep -qE "3\.[89]|3\.1[0-9]" || \
  err "Python 3.8+ required. Install from python.org"
log "Python: $($PYTHON --version)"

# ── Virtual environment ───────────────────────────────────────
if [ ! -d "venv" ]; then
  log "Creating virtual environment..."
  $PYTHON -m venv venv
fi
source venv/bin/activate
log "Virtual environment activated"

# ── Install dependencies ──────────────────────────────────────
log "Installing dependencies..."
pip install -r requirements.txt -q
log "Dependencies installed"

# ── Try PostgreSQL, fall back to SQLite ───────────────────────
PG_AVAILABLE=false
PG_BIN=""

for dir in /usr/local/opt/postgresql@*/bin /usr/local/opt/postgresql/bin /usr/local/bin; do
  if [ -f "$dir/pg_ctl" ]; then
    PG_BIN="$dir"
    PG_AVAILABLE=true
    break
  fi
done

if $PG_AVAILABLE; then
  log "PostgreSQL found at $PG_BIN"

  # Find data dir
  PG_DATA=""
  for data in /usr/local/var/postgresql@*/ /usr/local/var/postgres /usr/local/var/postgresql; do
    for expanded in $data; do
      if [ -f "$expanded/PG_VERSION" ]; then
        PG_DATA="$expanded"
        break 2
      fi
    done
  done

  if [ -z "$PG_DATA" ]; then
    warn "PostgreSQL data dir not found — initialising..."
    PG_DATA="/usr/local/var/postgres"
    "$PG_BIN/initdb" -D "$PG_DATA" --encoding=UTF8 --locale=C
  fi

  # Start PostgreSQL
  if ! "$PG_BIN/pg_ctl" status -D "$PG_DATA" > /dev/null 2>&1; then
    log "Starting PostgreSQL..."
    "$PG_BIN/pg_ctl" start -D "$PG_DATA" -l /tmp/mellow_pg.log -w
    sleep 2
  fi

  # Create user and database
  "$PG_BIN/psql" postgres -tAc \
    "SELECT 1 FROM pg_roles WHERE rolname='mellow'" | grep -q 1 || {
    "$PG_BIN/createuser" -s mellow 2>/dev/null || true
    "$PG_BIN/psql" postgres -c \
      "ALTER USER mellow WITH PASSWORD 'mellow';" > /dev/null
  }

  "$PG_BIN/psql" -U mellow -lqt | cut -d \| -f 1 | grep -qw mellow || {
    log "Creating database 'mellow'..."
    "$PG_BIN/createdb" -O mellow mellow
  }

  DB_URL="postgresql+asyncpg://mellow:mellow@localhost:5432/mellow"
  log "PostgreSQL ready"

else
  warn "PostgreSQL not found — using SQLite for local development"
  pip install aiosqlite -q
  DB_URL="sqlite+aiosqlite:///./mellow_local.db"
  warn "Note: SQLite is for local testing only, not production"
fi

# ── Create .env ───────────────────────────────────────────────
if [ ! -f ".env" ]; then
  log "Creating .env..."
  SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  JWT=$(python3 -c "import secrets; print(secrets.token_hex(32))")

  cat > .env << EOF
APP_NAME=Mellow
APP_ENV=development
DEBUG=True
SECRET_KEY=$SECRET
JWT_SECRET=$JWT
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30
DATABASE_URL=$DB_URL
REDIS_URL=
FRONTEND_URL=http://localhost:5500
ALLOWED_ORIGINS=http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000
FREE_DAILY_SWIPES=10
FREE_MESSAGES_PER_MATCH=3
FREE_MAX_PHOTOS=2
KINDRED_MAX_PHOTOS=6
KINDRED_PLUS_MAX_PHOTOS=6
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_KINDRED_PRICE_ID=
STRIPE_KINDRED_PLUS_PRICE_ID=
SENDGRID_API_KEY=
EOF
  log ".env created"
fi

# ── SQLite compatibility patch ────────────────────────────────
if [[ "$DB_URL" == *"sqlite"* ]]; then
  warn "Patching database.py for SQLite compatibility..."
  cat > _sqlite_patch.py << 'PYEOF'
"""Patch database.py to support SQLite for local dev."""
import re

with open("app/database.py", "r") as f:
    content = f.read()

# Remove pool settings incompatible with SQLite
content = content.replace(
    """    echo=settings.DEBUG,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,""",
    """    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},"""
)

with open("app/database.py", "w") as f:
    f.write(content)
print("SQLite patch applied")
PYEOF
  python3 _sqlite_patch.py
  rm _sqlite_patch.py
fi

# ── Start server ──────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════"
log "Starting Mellow backend..."
echo ""
echo "  API:    http://localhost:8000"
echo "  Docs:   http://localhost:8000/docs"
echo "  Health: http://localhost:8000/health"
echo ""
echo "  Frontend: open a new terminal and run:"
echo "  cd ../frontend && python3 -m http.server 5500"
echo ""
echo "  Press Ctrl+C to stop"
echo "════════════════════════════════════════"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000
