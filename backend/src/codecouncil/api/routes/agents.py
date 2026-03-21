"""Agent info and memory endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.api.deps import get_db
from codecouncil.db.repositories import AgentMemoryRepository, PersonaRepository

router = APIRouter(tags=["agents"])

# In-memory store for custom agents
_custom_agents: dict[str, dict[str, Any]] = {}


class CreateAgentRequest(BaseModel):
    handle: str  # unique identifier (lowercase, no spaces)
    name: str  # display name
    role: str  # short role description
    color: str  # hex color
    persona_prompt: str  # the agent's personality/instructions
    focus_areas: list[str] = []
    debate_role: str = "analyst"  # analyst | challenger | proposer
    temperature: float = 0.3
    vote_weight: float = 1.0


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
async def list_agents(db: AsyncSession | None = Depends(get_db)) -> dict:
    """Return metadata for all registered agents, including custom ones."""
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

    # Add in-memory custom agents
    for _handle, agent in _custom_agents.items():
        normalized.append(agent)

    # Also load persisted custom agents from DB
    if db is not None:
        try:
            repo = PersonaRepository(db)
            personas = await repo.list_personas()
            for p in personas:
                if p.name.startswith("agent:"):
                    agent_data = json.loads(p.content)
                    handle = agent_data.get("handle", "")
                    # Avoid duplicates with in-memory store
                    if handle not in _custom_agents:
                        normalized.append(agent_data)
        except Exception:
            pass  # DB may not be available

    return {"agents": normalized}


@router.post("/agents")
async def create_agent(
    request: CreateAgentRequest,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Create a custom agent."""
    # Check not colliding with built-in agents
    if request.handle in _VALID_HANDLES:
        raise HTTPException(
            status_code=400,
            detail=f"Handle '{request.handle}' conflicts with a built-in agent",
        )

    agent: dict[str, Any] = {
        "id": request.handle,
        "handle": request.handle,
        "name": request.name,
        "role": request.role,
        "color": request.color,
        "persona_prompt": request.persona_prompt,
        "focus_areas": request.focus_areas,
        "debate_role": request.debate_role,
        "temperature": request.temperature,
        "vote_weight": request.vote_weight,
        "is_custom": True,
    }
    _custom_agents[request.handle] = agent

    # Also persist to DB as a persona
    if db is not None:
        try:
            repo = PersonaRepository(db)
            await repo.create_persona(
                name=f"agent:{request.handle}",
                content=json.dumps(agent),
                is_default=False,
            )
            await db.commit()
        except Exception:
            pass  # Best-effort DB persistence

    return agent


@router.delete("/agents/{handle}")
async def delete_agent(
    handle: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Delete a custom agent."""
    if handle in _VALID_HANDLES:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete built-in agents",
        )

    removed = handle in _custom_agents
    if handle in _custom_agents:
        del _custom_agents[handle]

    # Also delete from DB
    if db is not None:
        try:
            repo = PersonaRepository(db)
            await repo.delete_persona(f"agent:{handle}")
            await db.commit()
            removed = True
        except Exception:
            pass

    if not removed:
        raise HTTPException(status_code=404, detail=f"Custom agent '{handle}' not found")

    return {"handle": handle, "deleted": True}


@router.get("/agents/{handle}/memory")
async def get_agent_memory(
    handle: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Return persisted memory summaries for an agent."""
    if handle not in _VALID_HANDLES and handle not in _custom_agents:
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
    if handle not in _VALID_HANDLES and handle not in _custom_agents:
        raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found")

    if db is not None:
        repo = AgentMemoryRepository(db)
        await repo.clear_memory(handle)
        await db.commit()
        return {"handle": handle, "cleared": True}

    # Fallback: in-memory
    _memory_store[handle] = []
    return {"handle": handle, "cleared": True}
