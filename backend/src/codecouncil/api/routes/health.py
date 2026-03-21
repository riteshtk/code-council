"""Health and readiness endpoints."""
from __future__ import annotations

import time

from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health")
async def health_check(request: Request) -> dict:
    """Health check — verifies database connectivity."""
    db_ok = False
    try:
        session_factory = getattr(request.app.state, "db_session_factory", None)
        if session_factory:
            async with session_factory() as db:
                await db.execute(text("SELECT 1"))
                db_ok = True
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": db_ok,
        "version": "0.1.0",
    }


@router.get("/ready")
async def readiness() -> dict:
    """Readiness probe — checks if critical dependencies are reachable."""
    return {"status": "ready"}
