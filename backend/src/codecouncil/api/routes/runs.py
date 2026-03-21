"""Run management endpoints."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.api.deps import get_db
from codecouncil.api.pipeline import run_real_council
from codecouncil.db.repositories import (
    EventRepository,
    FindingRepository,
    ProposalRepository,
    RunRepository,
    VoteRepository,
)

router = APIRouter(tags=["runs"])

logger = logging.getLogger("codecouncil.runs")


def _handle_task_error(task: asyncio.Task) -> None:
    """Log any unhandled exceptions from background pipeline tasks."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc:
        logger.error("Pipeline task failed: %s", exc, exc_info=exc)

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


def _orm_run_to_dict(r, *, findings=None, proposals=None, votes=None, events=None, rfc_content="") -> dict:
    """Convert an ORM RunModel into the normalised dict the frontend expects."""
    findings = findings or []
    proposals = proposals or []
    votes = votes or []
    events = events or []
    return {
        "id": str(r.id),
        "status": r.status or "pending",
        "phase": r.phase or "init",
        "repo": {"url": r.repo_url or "", "local_path": ""},
        "total_cost": r.total_cost_usd or 0,
        "finding_count": len(findings),
        "proposal_count": len(proposals),
        "created_at": r.started_at.isoformat() if r.started_at else "",
        "updated_at": (
            r.completed_at.isoformat()
            if r.completed_at
            else r.started_at.isoformat()
            if r.started_at
            else ""
        ),
        "consensus_score": r.consensus_score or 0,
        "has_rfc": bool(rfc_content),
        "rfc_content": rfc_content,
        "config_overrides": r.config_snapshot or {},
        "findings": [_orm_finding_to_dict(f) for f in findings],
        "proposals": [_orm_proposal_to_dict(p, votes) for p in proposals],
        "votes": [_orm_vote_to_dict(v) for v in votes],
        "events": [_orm_event_to_dict(e) for e in events],
        "debate_rounds": [],  # Could reconstruct from events
    }


def _orm_finding_to_dict(f) -> dict:
    return {
        "id": str(f.id),
        "run_id": str(f.run_id),
        "agent": f.agent,
        "agent_id": f.agent,
        "severity": f.severity,
        "content": f.content,
        "title": f.content[:200] if f.content else "",
        "description": f.content,
        "implication": f.implication or "",
        "scope": f.scope or "",
        "phase": "analysis",
        "tags": [],
        "created_at": f.created_at.isoformat() if f.created_at else "",
    }


def _orm_proposal_to_dict(p, all_votes) -> dict:
    p_votes = [_orm_vote_to_dict(v) for v in all_votes if v.proposal_id == p.id]
    return {
        "id": str(p.id),
        "run_id": str(p.run_id),
        "proposal_number": p.proposal_number,
        "version": p.version,
        "title": p.title,
        "goal": p.goal or "",
        "description": p.goal or "",
        "effort": p.effort or "M",
        "status": p.status or "proposed",
        "author_agent": p.author_agent or "",
        "agent_id": p.author_agent or "",
        "breaking_change": False,
        "finding_ids": [],
        "votes": p_votes,
        "created_at": p.created_at.isoformat() if p.created_at else "",
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
    }


def _orm_vote_to_dict(v) -> dict:
    return {
        "id": str(v.id),
        "run_id": str(v.run_id),
        "proposal_id": str(v.proposal_id),
        "agent": v.agent,
        "agent_id": v.agent,
        "vote": v.vote,
        "vote_type": "approve" if v.vote == "YES" else "reject" if v.vote == "NO" else "abstain",
        "rationale": v.rationale or "",
        "reasoning": v.rationale or "",
        "confidence": v.confidence or 0.5,
        "created_at": v.created_at.isoformat() if v.created_at else "",
    }


def _orm_event_to_dict(e) -> dict:
    return {
        "id": str(e.id),
        "event_id": str(e.id),
        "run_id": str(e.run_id),
        "agent": e.agent,
        "agent_id": e.agent,
        "type": e.event_type,
        "event_type": e.event_type,
        "phase": e.phase or "",
        "round": e.round,
        "content": e.content or "",
        "structured": e.structured or {},
        "payload": e.structured or {},
        "timestamp": e.created_at.isoformat() if e.created_at else "",
        "sequence": e.sequence or 0,
        "metadata": {
            "provider": e.provider or "",
            "model": e.model or "",
            "input_tokens": e.input_tokens or 0,
            "output_tokens": e.output_tokens or 0,
            "cost_usd": e.cost_usd or 0,
            "latency_ms": e.latency_ms or 0,
            "cached": e.cached or False,
        },
    }


async def _load_rfc_from_events(event_repo: EventRepository, run_id) -> str:
    """Extract RFC content from the rfc_generated event."""
    rfc_events = await event_repo.get_events_for_run(
        run_id, event_type="rfc_generated", limit=1,
    )
    if rfc_events:
        return rfc_events[0].content or ""
    # Fallback: try scribe agent_response from scribing phase
    scribe_events = await event_repo.get_events_for_run(
        run_id, agent="scribe", event_type="agent_response", phase="scribing", limit=1,
    )
    if scribe_events:
        return scribe_events[0].content or ""
    return ""


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
    task = asyncio.create_task(run_real_council(run, _runs, session_factory=session_factory))
    task.add_done_callback(_handle_task_error)
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
        finding_repo = FindingRepository(db)
        proposal_repo = ProposalRepository(db)
        event_repo = EventRepository(db)
        db_runs = await repo.list_runs(limit=200, offset=0)
        for r in db_runs:
            rid = str(r.id)
            db_run_ids.add(rid)
            live = _runs.get(rid)
            if live:
                results.append(_normalize_run(live))
            else:
                findings = await finding_repo.get_findings_for_run(r.id)
                proposals = await proposal_repo.get_proposals_for_run(r.id)
                # Lightweight RFC check: just see if the event exists
                rfc_events = await event_repo.get_events_for_run(
                    r.id, event_type="rfc_generated", limit=1,
                )
                has_rfc_marker = "yes" if rfc_events else ""
                results.append(_orm_run_to_dict(
                    r, findings=findings, proposals=proposals, rfc_content=has_rfc_marker,
                ))

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
            finding_repo = FindingRepository(db)
            proposal_repo = ProposalRepository(db)
            vote_repo = VoteRepository(db)
            event_repo = EventRepository(db)

            findings = await finding_repo.get_findings_for_run(uid)
            proposals = await proposal_repo.get_proposals_for_run(uid)
            votes = await vote_repo.get_votes_for_run(uid)
            events = await event_repo.get_events_for_run(uid, limit=500)

            rfc_content = await _load_rfc_from_events(event_repo, uid)

            return _orm_run_to_dict(
                r,
                findings=findings,
                proposals=proposals,
                votes=votes,
                events=events,
                rfc_content=rfc_content,
            )

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
        event_repo = EventRepository(db)
        rfc = await _load_rfc_from_events(event_repo, uid)
        if not rfc:
            rfc = f"# RFC for {r.repo_url}\n\n*No RFC content available.*\n"
        # Build norm with basic data for JSON format
        findings = await FindingRepository(db).get_findings_for_run(uid)
        proposals = await ProposalRepository(db).get_proposals_for_run(uid)
        votes = await VoteRepository(db).get_votes_for_run(uid)
        norm = _orm_run_to_dict(r, findings=findings, proposals=proposals, votes=votes, rfc_content=rfc)
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
    task = asyncio.create_task(run_real_council(new_run, _runs, session_factory=session_factory))
    task.add_done_callback(_handle_task_error)
    return _normalize_run(new_run)
