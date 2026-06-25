"""
Mellow — Rate Limiter Middleware
Simplified no-op version — avoids Redis async/greenlet conflicts.
Re-enable Redis rate limiting once core app is stable.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger("mellow.ratelimit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Pass-through middleware — no Redis calls.
    Rate limiting will be re-enabled in a future update.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        return await call_next(request)
