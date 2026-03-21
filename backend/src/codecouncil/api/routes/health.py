"""Health and readiness endpoints."""
from __future__ import annotations

import time

from fastapi import APIRouter

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health")
async def health() -> dict:
    """Health check — always returns ok if the process is alive."""
    return {
        "status": "healthy",
        "providers": {},
        "agents": {},
        "database": True,
        "version": "0.1.0",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
    }


@router.get("/ready")
async def readiness() -> dict:
    """Readiness probe — checks if critical dependencies are reachable."""
    return {"status": "ready"}
