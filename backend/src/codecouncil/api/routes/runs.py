"""Run management endpoints."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.api.deps import get_db
from codecouncil.api.pipeline import run_real_council
from codecouncil.db.repositories import EventRepository, RunRepository

router = APIRouter(tags=["runs"])

# ---------------------------------------------------------------------------
# In-memory store for **in-progress** runs (pipeline background task mutates
# these for WebSocket streaming).  Completed runs live only in the DB.
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


def _orm_run_to_dict(r) -> dict:
    """Convert an ORM RunModel into the normalised dict the frontend expects."""
    return {
        "id": str(r.id),
        "status": r.status or "pending",
        "phase": r.phase or "init",
        "repo": {"url": r.repo_url or "", "local_path": ""},
        "total_cost": r.total_cost_usd or 0,
        "finding_count": 0,
        "proposal_count": 0,
        "created_at": r.started_at.isoformat() if r.started_at else "",
        "updated_at": (
            r.completed_at.isoformat()
            if r.completed_at
            else r.started_at.isoformat()
            if r.started_at
            else ""
        ),
        "consensus_score": r.consensus_score or 0,
        "has_rfc": False,
        "config_overrides": r.config_snapshot or {},
        "findings": [],
        "proposals": [],
        "votes": [],
        "events": [],
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
async def create_run(
    request: Request,
    body: CreateRunRequest,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Start a new council run."""
    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Persist to DB
    if db is not None:
        repo = RunRepository(db)
        await repo.create_run(
            run_id=uuid.UUID(run_id),
            repo_url=body.repo_url,
            repo_name=body.repo_url.rstrip("/").split("/")[-1].replace(".git", ""),
            config_snapshot=body.config_overrides or {},
        )
        await db.commit()

    # Also keep in _runs for the pipeline background task
    run = {
        "run_id": run_id,
        "repo_url": body.repo_url,
        "config_overrides": body.config_overrides or {},
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
    session_factory = getattr(request.app.state, "db_session_factory", None)
    asyncio.create_task(
        run_real_council(run, _runs, session_factory=session_factory)
    )
    return _normalize_run(run)


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """List all runs."""
    results: list[dict] = []
    db_run_ids: set[str] = set()

    if db is not None:
        repo = RunRepository(db)
        db_runs = await repo.list_runs(limit=200, offset=0)
        for r in db_runs:
            rid = str(r.id)
            db_run_ids.add(rid)
            live = _runs.get(rid)
            if live:
                results.append(_normalize_run(live))
            else:
                results.append(_orm_run_to_dict(r))

    # Add any in-progress runs not yet in DB (or if DB is unavailable)
    for rid, run in _runs.items():
        if rid not in db_run_ids:
            results.append(_normalize_run(run))

    if status:
        results = [r for r in results if r.get("status") == status]

    results.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    total = len(results)
    paginated = results[offset: offset + limit]

    return {"runs": paginated, "total": total, "limit": limit, "offset": offset}


@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: AsyncSession | None = Depends(get_db)) -> dict:
    """Get full run state."""
    live = _runs.get(run_id)
    if live:
        return _normalize_run(live)

    if db is not None:
        try:
            uid = uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        repo = RunRepository(db)
        r = await repo.get_run(uid)
        if r is not None:
            return _orm_run_to_dict(r)

    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


@router.delete("/runs/{run_id}")
async def cancel_run(run_id: str, db: AsyncSession | None = Depends(get_db)) -> dict:
    """Delete/cancel a run."""
    _runs.pop(run_id, None)

    if db is not None:
        try:
            uid = uuid.UUID(run_id)
            repo = RunRepository(db)
            await repo.delete_run(uid)
            await db.commit()
        except ValueError:
            pass

    return {"id": run_id, "status": "deleted"}


@router.post("/runs/{run_id}/review")
async def submit_review(
    run_id: str,
    review: ReviewRequest,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Submit a human challenge/override for a run."""
    run = _runs.get(run_id)
    if run is None and db is not None:
        try:
            uid = uuid.UUID(run_id)
            repo = RunRepository(db)
            r = await repo.get_run(uid)
            if r is None:
                raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    elif run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return {"id": run_id, "review_type": review.type, "accepted": True}


@router.get("/runs/{run_id}/rfc")
async def get_rfc(
    run_id: str,
    format: str = Query(default="markdown"),
    db: AsyncSession | None = Depends(get_db),
) -> Response:
    """Get the RFC document in the specified format."""
    import json as _json

    run = _runs.get(run_id)
    if run:
        rfc = run.get("rfc_content", "")
        if not rfc:
            rfc = f"# RFC for {run.get('repo_url', 'unknown')}\n\n*Analysis in progress...*\n"
        norm = _normalize_run(run)
    elif db is not None:
        try:
            uid = uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        repo = RunRepository(db)
        r = await repo.get_run(uid)
        if r is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        norm = _orm_run_to_dict(r)
        event_repo = EventRepository(db)
        events = await event_repo.get_events_for_run(
            uid, event_type="agent_response", phase="scribing", limit=1,
        )
        if events:
            rfc = events[0].content or ""
        else:
            rfc = f"# RFC for {r.repo_url}\n\n*No RFC content available.*\n"
    else:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if format == "json":
        return Response(
            content=_json.dumps({**norm, "rfc_content": rfc}, indent=2),
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
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Get events for a run with optional filtering."""
    run = _runs.get(run_id)
    if run:
        events = run.get("events", [])
        if agent:
            events = [e for e in events if e.get("agent") == agent]
        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]
        paginated = events[offset: offset + limit]
        return {"events": paginated, "total": len(events)}

    if db is not None:
        try:
            uid = uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        event_repo = EventRepository(db)
        db_events = await event_repo.get_events_for_run(
            uid, agent=agent, event_type=event_type, limit=limit, offset=offset,
        )
        events_out = []
        for e in db_events:
            events_out.append({
                "id": str(e.id),
                "event_id": str(e.id),
                "run_id": str(e.run_id),
                "agent": e.agent,
                "agent_id": e.agent,
                "type": e.event_type,
                "event_type": e.event_type,
                "content": e.content,
                "phase": e.phase,
                "timestamp": e.created_at.isoformat() if e.created_at else "",
                "sequence": e.sequence,
                "structured": e.structured or {},
                "payload": e.structured or {},
                "metadata": {
                    "provider": e.provider or "",
                    "model": e.model or "",
                    "input_tokens": e.input_tokens or 0,
                    "output_tokens": e.output_tokens or 0,
                    "cost_usd": e.cost_usd or 0,
                },
            })
        return {"events": events_out, "total": len(events_out)}

    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


@router.get("/runs/{run_id}/cost")
async def get_cost(run_id: str, db: AsyncSession | None = Depends(get_db)) -> dict:
    """Get cost breakdown for a run."""
    live = _runs.get(run_id)
    if live:
        return {
            "run_id": run_id,
            "total_cost": live.get("cost_usd", 0) or 0,
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "by_agent": {},
            "by_phase": {},
            "currency": "USD",
        }

    if db is not None:
        try:
            uid = uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        repo = RunRepository(db)
        r = await repo.get_run(uid)
        if r is not None:
            return {
                "run_id": run_id,
                "total_cost": r.total_cost_usd or 0,
                "total_tokens": 0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "by_agent": {},
                "by_phase": {},
                "currency": "USD",
            }

    raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")


@router.post("/runs/{run_id}/rerun", status_code=201)
async def rerun(
    run_id: str,
    request: Request,
    db: AsyncSession | None = Depends(get_db),
) -> dict:
    """Re-run the same analysis with the same or modified config."""
    run = _runs.get(run_id)
    repo_url: str
    config_overrides: dict

    if run:
        repo_url = run["repo_url"]
        config_overrides = run.get("config_overrides", {})
    elif db is not None:
        try:
            uid = uuid.UUID(run_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        run_repo = RunRepository(db)
        r = await run_repo.get_run(uid)
        if r is None:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        repo_url = r.repo_url
        config_overrides = r.config_snapshot or {}
    else:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    new_run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    if db is not None:
        repo = RunRepository(db)
        await repo.create_run(
            run_id=uuid.UUID(new_run_id),
            repo_url=repo_url,
            repo_name=repo_url.rstrip("/").split("/")[-1].replace(".git", ""),
            config_snapshot=config_overrides,
        )
        await db.commit()

    new_run = {
        "run_id": new_run_id,
        "repo_url": repo_url,
        "config_overrides": config_overrides,
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

    session_factory = getattr(request.app.state, "db_session_factory", None)
    asyncio.create_task(
        run_real_council(new_run, _runs, session_factory=session_factory)
    )
    return _normalize_run(new_run)
