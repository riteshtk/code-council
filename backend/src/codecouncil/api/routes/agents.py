"""Agent info and memory endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

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

# In-memory memory store (keyed by handle -> list of memory summaries)
_memory_store: dict[str, list[dict]] = {a["handle"]: [] for a in _AGENT_METADATA}


@router.get("/agents")
async def list_agents() -> dict:
    """Return metadata for all registered agents."""
    return {"agents": _AGENT_METADATA}


@router.get("/agents/{handle}/memory")
async def get_agent_memory(handle: str) -> dict:
    """Return persisted memory summaries for an agent."""
    if handle not in _memory_store:
        raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found")
    return {"handle": handle, "memory": _memory_store[handle]}


@router.delete("/agents/{handle}/memory")
async def clear_agent_memory(handle: str) -> dict:
    """Clear all persisted memory for an agent."""
    if handle not in _memory_store:
        raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found")
    _memory_store[handle] = []
    return {"handle": handle, "cleared": True}
