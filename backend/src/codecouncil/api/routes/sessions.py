"""Session history endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.api.deps import get_db
from codecouncil.db.repositories import SessionRepository

router = APIRouter(tags=["sessions"])

# In-memory session store — used as fallback when DB is unavailable
_sessions: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateSessionRequest(BaseModel):
    name: str
    run_ids: list[str] | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_to_dict(model: Any) -> dict:
    """Convert a SessionModel to a plain dict."""
    return {
        "id": str(model.id),
        "name": model.name,
        "run_ids": model.run_ids or [],
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Return paginated list of sessions."""
    if db is not None:
        repo = SessionRepository(db)
        rows = await repo.list_sessions(limit=limit, offset=offset)
        sessions = [_model_to_dict(r) for r in rows]
        return {"sessions": sessions, "total": len(sessions)}

    # Fallback: in-memory
    all_sessions = list(_sessions.values())
    paginated = all_sessions[offset: offset + limit]
    return {"sessions": paginated, "total": len(all_sessions)}


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Create a new named session."""
    if db is not None:
        repo = SessionRepository(db)
        model = await repo.create_session(name=body.name, run_ids=body.run_ids)
        await db.commit()
        return _model_to_dict(model)

    # Fallback: in-memory
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
async def compare_sessions(
    ids: list[str] = Query(default=[]),
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Compare multiple sessions side-by-side."""
    compared = []
    if db is not None:
        repo = SessionRepository(db)
        for sid in ids:
            try:
                model = await repo.get_session(uuid.UUID(sid))
                if model:
                    compared.append(_model_to_dict(model))
            except ValueError:
                continue
    else:
        for sid in ids:
            sess = _sessions.get(sid)
            if sess:
                compared.append(sess)
    return {"sessions": compared, "count": len(compared)}


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Get a specific session by ID."""
    if db is not None:
        repo = SessionRepository(db)
        try:
            model = await repo.get_session(uuid.UUID(session_id))
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        if model is None:
            raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
        return _model_to_dict(model)

    # Fallback: in-memory
    session = _sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session
