"""Middleware for CodeCouncil API: CORS, logging, rate limiting, error handling."""
from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rate limiter (simple in-memory, 100 req/min per IP)
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Simple sliding-window rate limiter keyed by IP."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> bool:
        now = time.monotonic()
        bucket = self._buckets[ip]
        # Drop timestamps outside the window
        cutoff = now - self.window
        self._buckets[ip] = [t for t in bucket if t > cutoff]
        if len(self._buckets[ip]) >= self.max_requests:
            return False
        self._buckets[ip].append(now)
        return True


_rate_limiter = _RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        if not _rate_limiter.is_allowed(ip):
            return JSONResponse(
                {"detail": "Too many requests. Try again in a minute."},
                status_code=429,
            )
        return await call_next(request)


# ---------------------------------------------------------------------------
# Request logging middleware
# ---------------------------------------------------------------------------

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


# ---------------------------------------------------------------------------
# Error-handler middleware
# ---------------------------------------------------------------------------

async def _global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error for %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def add_middleware(app: FastAPI) -> None:
    """Attach all middleware layers to *app*."""
    # CORS — permissive for development; tighten via env/config in production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    app.add_middleware(RateLimitMiddleware)

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    # Global unhandled exception handler
    app.add_exception_handler(Exception, _global_exception_handler)
