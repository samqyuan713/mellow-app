"""
Mellow — Rate Limiter Middleware
Redis-based sliding window rate limiting.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import redis.asyncio as aioredis
import time
import logging

from app.config import settings

logger = logging.getLogger("mellow.ratelimit")

# Rate limit rules per route prefix
RATE_RULES = {
    "/api/v1/auth":     {"limit": 10,  "window": 60},   # 10 req/min on auth
    "/api/v1/matches/swipe": {"limit": 60, "window": 60},
    "default":          {"limit": 60,  "window": 60},   # 60 req/min general
}


class RateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self._redis = None

    async def get_redis(self):
        if self._redis is None:
            try:
                self._redis = await aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Redis unavailable for rate limiting: {e}")
                return None
        return self._redis

    def get_rule(self, path: str) -> dict:
        for prefix, rule in RATE_RULES.items():
            if prefix != "default" and path.startswith(prefix):
                return rule
        return RATE_RULES["default"]

    async def dispatch(self, request: Request, call_next) -> Response:
        """No-op rate limiter — re-enable once Redis async is fixed."""
        return await call_next(request)
        
        # Skip rate limiting for health check
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        redis = await self.get_redis()
        if not redis:
            # If Redis is down, allow requests through (fail open)
            return await call_next(request)

        # Identify client: prefer user ID from header, fall back to IP
        client_id = (
            request.headers.get("X-User-ID") or
            request.client.host or
            "unknown"
        )

        rule    = self.get_rule(request.url.path)
        limit   = rule["limit"]
        window  = rule["window"]
        key     = f"rate:{client_id}:{request.url.path.split('/')[3] if len(request.url.path.split('/')) > 3 else 'root'}"
        now     = int(time.time())
        window_start = now - window

        try:
            pipe = redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)     # remove old entries
            pipe.zadd(key, {str(now): now})                  # add current request
            pipe.zcard(key)                                  # count in window
            pipe.expire(key, window)                         # auto-expire key
            results = await pipe.execute()
            request_count = results[2]

            # Set rate limit headers
            headers = {
                "X-RateLimit-Limit":     str(limit),
                "X-RateLimit-Remaining": str(max(0, limit - request_count)),
                "X-RateLimit-Reset":     str(now + window),
            }

            if request_count > limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many requests. Please slow down."},
                    headers=headers,
                )

            response = await call_next(request)
            for key_h, val in headers.items():
                response.headers[key_h] = val
            return response

        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return await call_next(request)
