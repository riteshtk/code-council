"""Agent info and memory endpoints."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
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
async def list_agents(request: Request, db: AsyncSession | None = Depends(get_db)) -> dict:
    """Return metadata for all registered agents, including custom ones."""
    registry = getattr(request.app.state, "agent_registry", None)
    agents_list: list[dict] = []

    if registry:
        for defn in registry.list_all():
            agents_list.append(defn.to_api_dict())
    else:
        # Fallback to hardcoded defaults
        agents_list = [
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
            agents_list.append(agent)

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
                            agents_list.append(agent_data)
            except Exception:
                pass  # DB may not be available

    return {"agents": agents_list}


@router.post("/agents")
async def create_agent(
    request_body: CreateAgentRequest,
    request: Request,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Create a custom agent."""
    # Check not colliding with built-in agents
    registry = getattr(request.app.state, "agent_registry", None)
    if request_body.handle in _VALID_HANDLES:
        raise HTTPException(
            status_code=400,
            detail=f"Handle '{request_body.handle}' conflicts with a built-in agent",
        )
    if registry and registry.get(request_body.handle) and registry.get(request_body.handle).is_builtin:
        raise HTTPException(
            status_code=400,
            detail=f"Handle '{request_body.handle}' conflicts with a built-in agent",
        )

    agent: dict[str, Any] = {
        "id": request_body.handle,
        "handle": request_body.handle,
        "name": request_body.name,
        "role": request_body.role,
        "color": request_body.color,
        "persona_prompt": request_body.persona_prompt,
        "focus_areas": request_body.focus_areas,
        "debate_role": request_body.debate_role,
        "temperature": request_body.temperature,
        "vote_weight": request_body.vote_weight,
        "is_custom": True,
    }
    _custom_agents[request_body.handle] = agent

    # Register in the agent registry
    if registry:
        from codecouncil.agents.definition import AgentDefinition

        defn = AgentDefinition(
            handle=request_body.handle,
            name=request_body.name,
            abbr=request_body.handle[:2].upper(),
            role=request_body.role,
            short_role=request_body.debate_role,
            color=request_body.color,
            icon="user",
            description=request_body.role,
            debate_role=request_body.debate_role,
            temperature=request_body.temperature,
            vote_weight=request_body.vote_weight,
            persona=request_body.persona_prompt,
            focus_areas=request_body.focus_areas,
            is_builtin=False,
        )
        registry.register(defn)

    # Also persist to DB as a persona
    if db is not None:
        try:
            repo = PersonaRepository(db)
            await repo.create_persona(
                name=f"agent:{request_body.handle}",
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
    request: Request,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Delete a custom agent."""
    if handle in _VALID_HANDLES:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete built-in agents",
        )

    registry = getattr(request.app.state, "agent_registry", None)
    if registry:
        existing = registry.get(handle)
        if existing and existing.is_builtin:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete built-in agents",
            )
        registry.unregister(handle)

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

    if not removed and not (registry and registry.get(handle) is None):
        raise HTTPException(status_code=404, detail=f"Custom agent '{handle}' not found")

    return {"handle": handle, "deleted": True}


@router.get("/agents/{handle}/memory")
async def get_agent_memory(
    handle: str,
    request: Request,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Return persisted memory summaries for an agent."""
    registry = getattr(request.app.state, "agent_registry", None)
    known = handle in _VALID_HANDLES or handle in _custom_agents or (registry and registry.get(handle) is not None)
    if not known:
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
    request: Request,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Clear all persisted memory for an agent."""
    registry = getattr(request.app.state, "agent_registry", None)
    known = handle in _VALID_HANDLES or handle in _custom_agents or (registry and registry.get(handle) is not None)
    if not known:
        raise HTTPException(status_code=404, detail=f"Agent '{handle}' not found")

    if db is not None:
        repo = AgentMemoryRepository(db)
        await repo.clear_memory(handle)
        await db.commit()
        return {"handle": handle, "cleared": True}

    # Fallback: in-memory
    _memory_store[handle] = []
    return {"handle": handle, "cleared": True}
