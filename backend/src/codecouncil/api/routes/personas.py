"""Persona CRUD endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.api.deps import get_db
from codecouncil.db.repositories import PersonaRepository

router = APIRouter(tags=["personas"])

# In-memory persona store — used as fallback when DB is unavailable
_personas: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreatePersonaRequest(BaseModel):
    name: str
    content: str
    is_default: bool = False


class UpdatePersonaRequest(BaseModel):
    content: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_to_dict(model: Any) -> dict:
    """Convert a PersonaModel to a plain dict."""
    return {
        "id": str(model.id),
        "name": model.name,
        "content": model.content,
        "is_default": model.is_default,
        "created_at": model.created_at.isoformat() if model.created_at else None,
        "updated_at": model.updated_at.isoformat() if model.updated_at else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/personas")
async def list_personas(
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Return all personas."""
    if db is not None:
        repo = PersonaRepository(db)
        rows = await repo.list_personas()
        return {"personas": [_model_to_dict(r) for r in rows]}

    return {"personas": list(_personas.values())}


@router.post("/personas", status_code=201)
async def create_persona(
    body: CreatePersonaRequest,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Create a new persona."""
    if db is not None:
        repo = PersonaRepository(db)
        existing = await repo.get_persona(body.name)
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"Persona '{body.name}' already exists")
        model = await repo.create_persona(
            name=body.name, content=body.content, is_default=body.is_default,
        )
        await db.commit()
        return _model_to_dict(model)

    # Fallback: in-memory
    if body.name in _personas:
        raise HTTPException(status_code=409, detail=f"Persona '{body.name}' already exists")
    now = datetime.now(tz=timezone.utc).isoformat()
    persona = {
        "id": str(uuid.uuid4()),
        "name": body.name,
        "content": body.content,
        "is_default": body.is_default,
        "created_at": now,
        "updated_at": now,
    }
    _personas[body.name] = persona
    return persona


@router.get("/personas/{name}")
async def get_persona(
    name: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Get a persona by name."""
    if db is not None:
        repo = PersonaRepository(db)
        model = await repo.get_persona(name)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
        return _model_to_dict(model)

    persona = _personas.get(name)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
    return persona


@router.put("/personas/{name}")
async def update_persona(
    name: str,
    body: UpdatePersonaRequest,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Update a persona's content."""
    if db is not None:
        repo = PersonaRepository(db)
        model = await repo.get_persona(name)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
        await repo.update_persona(name, body.content)
        await db.commit()
        # Re-fetch to get updated fields
        model = await repo.get_persona(name)
        return _model_to_dict(model)

    persona = _personas.get(name)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
    persona["content"] = body.content
    persona["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    return persona


@router.delete("/personas/{name}")
async def delete_persona(
    name: str,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Delete a persona."""
    if db is not None:
        repo = PersonaRepository(db)
        model = await repo.get_persona(name)
        if model is None:
            raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
        await repo.delete_persona(name)
        await db.commit()
        return {"name": name, "deleted": True}

    if name not in _personas:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
    del _personas[name]
    return {"name": name, "deleted": True}
