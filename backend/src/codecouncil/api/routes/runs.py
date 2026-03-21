"""Run management endpoints."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from codecouncil.api.pipeline import run_real_council

router = APIRouter(tags=["runs"])

# ---------------------------------------------------------------------------
# In-memory store for runs (DB integration deferred; no DB required in tests)
# ---------------------------------------------------------------------------
_runs: dict[str, dict] = {}


def _normalize_run(run: dict) -> dict:
    """Normalize a stored run dict into the shape the frontend expects."""
    run_id = run.get("run_id", run.get("id", ""))
    return {
        "id": run_id,
        "status": run.get("status", "pending"),
        "phase": run.get("phase", "init"),
        "repo": {
            "url": run.get("repo_url", ""),
            "local_path": run.get("local_path", ""),
        },
        "findings": run.get("findings", []),
        "proposals": run.get("proposals", []),
        "votes": run.get("votes", []),
        "events": run.get("events", []),
        "total_cost": run.get("cost_usd", 0) or 0,
        "finding_count": len(run.get("findings", [])),
        "proposal_count": len(run.get("proposals", [])),
        "created_at": run.get("created_at", ""),
        "updated_at": run.get("updated_at", ""),
        "config_overrides": run.get("config_overrides", {}),
        "consensus_score": 100.0 if run.get("status") == "completed" else 0.0,
        "has_rfc": bool(run.get("rfc_content")),
    }


# ---------------------------------------------------------------------------
# Pydantic request/response models
# ---------------------------------------------------------------------------

class CreateRunRequest(BaseModel):
    repo_url: str
    config_overrides: dict[str, Any] = {}


class ReviewRequest(BaseModel):
    type: str  # "challenge" | "override" | "approve" | "redebate"
    finding_id: str | None = None
    proposal_id: str | None = None
    content: str | None = None
    new_vote: str | None = None
    reason: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/runs", status_code=201)
async def create_run(request: CreateRunRequest) -> dict:
    """Start a new council run."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    run = {
        "run_id": run_id,
        "repo_url": request.repo_url,
        "config_overrides": request.config_overrides or {},
        "status": "pending",
        "phase": "init",
        "events": [],
        "findings": [],
        "proposals": [],
        "votes": [],
        "cost_usd": 0.0,
        "created_at": now,
        "updated_at": now,
    }
    _runs[run_id] = run
    # Launch real pipeline as background task
    asyncio.create_task(run_real_council(run, _runs))
    return _normalize_run(run)


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
) -> dict:
    """List all runs."""
    all_runs = list(_runs.values())
    if status:
        all_runs = [r for r in all_runs if r.get("status") == status]
    # Sort newest first
    all_runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    paginated = all_runs[offset: offset + limit]
    return {
        "runs": [_normalize_run(r) for r in paginated],
        "total": len(all_runs),
        "limit": limit,
        "offset": offset,
    }


@router.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    """Get full run state."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return _normalize_run(run)


@router.delete("/runs/{run_id}")
async def cancel_run(run_id: str) -> dict:
    """Delete/cancel a run."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    del _runs[run_id]
    return {"id": run_id, "status": "deleted"}


@router.post("/runs/{run_id}/review")
async def submit_review(run_id: str, review: ReviewRequest) -> dict:
    """Submit a human challenge/override for a run."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {"id": run_id, "review_type": review.type, "accepted": True}


@router.get("/runs/{run_id}/rfc")
async def get_rfc(run_id: str, format: str = Query(default="markdown")) -> Response:
    """Get the RFC document in the specified format."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    rfc = run.get("rfc_content", "")
    if not rfc:
        rfc = f"# RFC for {run.get('repo_url', 'unknown')}\n\n*Analysis in progress...*\n"

    if format == "json":
        import json
        return Response(
            content=json.dumps({**_normalize_run(run), "rfc_content": rfc}, indent=2),
            media_type="application/json",
        )
    if format == "html":
        html = (
            f"<html><body style='font-family:sans-serif;max-width:800px;"
            f"margin:0 auto;padding:20px;'>{rfc}</body></html>"
        )
        return Response(content=html, media_type="text/html")

    return Response(content=rfc, media_type="text/markdown")


@router.get("/runs/{run_id}/events")
async def get_events(
    run_id: str,
    agent: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    """Get events for a run with optional filtering."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    events = run.get("events", [])
    if agent:
        events = [e for e in events if e.get("agent") == agent]
    if event_type:
        events = [e for e in events if e.get("event_type") == event_type]
    paginated = events[offset: offset + limit]
    return {"events": paginated, "total": len(events)}


@router.get("/runs/{run_id}/cost")
async def get_cost(run_id: str) -> dict:
    """Get cost breakdown for a run."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {
        "run_id": run_id,
        "total_cost": run.get("cost_usd", 0) or 0,
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "by_agent": {},
        "by_phase": {},
        "currency": "USD",
    }


@router.post("/runs/{run_id}/rerun", status_code=201)
async def rerun(run_id: str) -> dict:
    """Re-run the same analysis with the same or modified config."""
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    new_run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    new_run = {
        "run_id": new_run_id,
        "repo_url": run["repo_url"],
        "config_overrides": run.get("config_overrides", {}),
        "status": "pending",
        "phase": "init",
        "events": [],
        "findings": [],
        "proposals": [],
        "votes": [],
        "cost_usd": 0.0,
        "created_at": now,
        "updated_at": now,
        "rerun_of": run_id,
    }
    _runs[new_run_id] = new_run
    asyncio.create_task(run_real_council(new_run, _runs))
    return _normalize_run(new_run)
