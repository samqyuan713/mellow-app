"""
Mellow Dating App — FastAPI Backend
"Designed for people who know what they want — and what they don't."
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from app.config import settings
from app.database import create_tables
from app.routers import auth, profiles, matches, messages, subscriptions, safety
from app.middleware.rate_limiter import RateLimitMiddleware

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("mellow")


# ── Lifespan (startup / shutdown) ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🌱 Mellow starting up...")
    await create_tables()
    logger.info("✅ Database tables ready")
    yield
    logger.info("👋 Mellow shutting down...")


# ── App Instance ───────────────────────────────────────────────
app = FastAPI(
    title="Mellow API",
    description="Backend API for Mellow — a dating app for meaningful connections",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)


# ── Middleware ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)

app.add_middleware(RateLimitMiddleware)

if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["mellow.app", "*.mellow.app", "*.railway.app"]
    )


# ── Routers ────────────────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/v1/auth",          tags=["Authentication"])
app.include_router(profiles.router,      prefix="/api/v1/profiles",       tags=["Profiles"])
app.include_router(matches.router,       prefix="/api/v1/matches",        tags=["Matches"])
app.include_router(messages.router,      prefix="/api/v1/messages",       tags=["Messages"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions",  tags=["Subscriptions"])
app.include_router(safety.router,        prefix="/api/v1/safety",         tags=["Safety"])


# ── Health Check ───────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "healthy", "app": "Mellow", "version": "1.0.0"}


# ── Root ───────────────────────────────────────────────────────
@app.get("/", tags=["System"])
async def root():
    return {
        "app": "💜 Mellow",
        "tagline": "Designed for people who know what they want — and what they don't.",
        "docs": "/docs",
        "version": "1.0.0"
    }


# ── Global Exception Handler ───────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."}
    )
