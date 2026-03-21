"""Session history endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(tags=["sessions"])

# In-memory session store {id: {...}}
_sessions: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    name: str
    run_ids: list[str] | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Return paginated list of sessions."""
    all_sessions = list(_sessions.values())
    paginated = all_sessions[offset: offset + limit]
    return {"sessions": paginated, "total": len(all_sessions)}


@router.post("/sessions", status_code=201)
async def create_session(body: CreateSessionRequest) -> dict:
    """Create a new named session."""
    session_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc).isoformat()
    session = {
        "id": session_id,
        "name": body.name,
        "run_ids": body.run_ids or [],
        "created_at": now,
    }
    _sessions[session_id] = session
    return session


@router.get("/sessions/compare")
async def compare_sessions(ids: list[str] = Query(default=[])) -> dict:
    """Compare multiple sessions side-by-side."""
    compared = []
    for sid in ids:
        sess = _sessions.get(sid)
        if sess:
            compared.append(sess)
    return {"sessions": compared, "count": len(compared)}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get a specific session by ID."""
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session
