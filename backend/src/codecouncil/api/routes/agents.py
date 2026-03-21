"""Agent info and memory endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.api.deps import get_db
from codecouncil.db.repositories import AgentMemoryRepository

router = APIRouter(tags=["agents"])

# Static metadata for the built-in agents
_AGENT_METADATA = [
    {
        "handle": "archaeologist",
        "name": "The Archaeologist",
        "description": "Analyses git history, churn, bus factor, dead code and test coverage.",
        "debate_role": "ANALYST",
        "color": "#8B4513",
    },
    {
        "handle": "skeptic",
        "name": "The Skeptic",
        "description": "Challenges proposals on security, performance and tech-debt grounds.",
        "debate_role": "CHALLENGER",
        "color": "#DC143C",
    },
    {
        "handle": "visionary",
        "name": "The Visionary",
        "description": "Proposes architectural improvements and modernisation paths.",
        "debate_role": "PROPOSER",
        "color": "#9370DB",
    },
    {
        "handle": "scribe",
        "name": "The Scribe",
        "description": "Synthesises debate output into a structured RFC document.",
        "debate_role": "SCRIBE",
        "color": "#2E8B57",
    },
]

_VALID_HANDLES = {a["handle"] for a in _AGENT_METADATA}

# In-memory memory store — used as fallback when DB is unavailable
_memory_store: dict[str, list[dict]] = {a["handle"]: [] for a in _AGENT_METADATA}


def _memory_model_to_dict(model: Any) -> dict:
    """Convert an AgentMemoryModel to a plain dict."""
    return {
        "id": str(model.id),
        "agent_handle": model.agent_handle,
        "session_id": str(model.session_id) if model.session_id else None,
        "summary": model.summary,
        "token_count": model.token_count,
        "created_at": model.created_at.isoformat() if model.created_at else None,
    }


@router.get("/agents")
async def list_agents() -> dict:
    """Return metadata for all registered agents."""
    normalized = [
        {
            "id": agent["handle"],
            "name": agent["name"],
            "role": agent["debate_role"],
            "color": agent["color"],
            "description": agent["description"],
            "handle": agent["handle"],
        }
        for agent in _AGENT_METADATA
    ]
    return {"agents": normalized}


@router.get("/agents/{handle}/memory")
async def get_agent_memory(
    handle: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Return persisted memory summaries for an agent."""
    if handle not in _VALID_HANDLES:
        raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found")

    if db is not None:
        repo = AgentMemoryRepository(db)
        rows = await repo.get_memory(handle)
        return {"handle": handle, "memory": [_memory_model_to_dict(r) for r in rows]}

    # Fallback: in-memory
    return {"handle": handle, "memory": _memory_store.get(handle, [])}


@router.delete("/agents/{handle}/memory")
async def clear_agent_memory(
    handle: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Clear all persisted memory for an agent."""
    if handle not in _VALID_HANDLES:
        raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found")

    if db is not None:
        repo = AgentMemoryRepository(db)
        await repo.clear_memory(handle)
        await db.commit()
        return {"handle": handle, "cleared": True}

    # Fallback: in-memory
    _memory_store[handle] = []
    return {"handle": handle, "cleared": True}
