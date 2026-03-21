"""Persona CRUD endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["personas"])

# In-memory persona store {name: {...}}
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
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/personas")
async def list_personas() -> dict:
    """Return all personas."""
    return {"personas": list(_personas.values())}


@router.post("/personas", status_code=201)
async def create_persona(body: CreatePersonaRequest) -> dict:
    """Create a new persona."""
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
async def get_persona(name: str) -> dict:
    """Get a persona by name."""
    persona = _personas.get(name)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
    return persona


@router.put("/personas/{name}")
async def update_persona(name: str, body: UpdatePersonaRequest) -> dict:
    """Update a persona's content."""
    persona = _personas.get(name)
    if persona is None:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
    persona["content"] = body.content
    persona["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
    return persona


@router.delete("/personas/{name}")
async def delete_persona(name: str) -> dict:
    """Delete a persona."""
    if name not in _personas:
        raise HTTPException(status_code=404, detail=f"Persona '{name}' not found")
    del _personas[name]
    return {"name": name, "deleted": True}
