# Database Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire PostgreSQL persistence so runs, events, findings, proposals, and votes survive server restarts.

**Architecture:** Initialize the DB engine in FastAPI lifespan, create a session dependency, replace the in-memory `_runs` dict in route handlers with repository calls, and update the pipeline to persist data as it runs.

**Tech Stack:** SQLAlchemy async + asyncpg (already installed), existing ORM models + repositories

---

## Current State

- 8 ORM models: fully built in `db/models.py`
- 8 repository classes: fully built in `db/repositories.py`
- DB engine factory: built in `db/engine.py`
- Alembic migration: applied, all tables exist in PostgreSQL
- **Gap:** App lifespan doesn't create engine, routes use `_runs` dict, pipeline writes to dict only

## Files to Modify

| File | Change |
|------|--------|
| `backend/src/codecouncil/api/app.py` | Add DB engine + session factory to lifespan |
| `backend/src/codecouncil/api/deps.py` | NEW — FastAPI dependency for DB session |
| `backend/src/codecouncil/api/routes/runs.py` | Replace `_runs` dict with repository calls |
| `backend/src/codecouncil/api/pipeline.py` | Persist events/findings/proposals/votes to DB |
| `backend/src/codecouncil/api/websocket.py` | Load events from DB for replay |

---

### Task 1: Initialize DB in App Lifespan + Create Session Dependency

**Files:**
- Modify: `backend/src/codecouncil/api/app.py`
- Create: `backend/src/codecouncil/api/deps.py`

- [ ] **Step 1: Update app.py lifespan to create DB engine and session factory**

In the lifespan, after EventBus init:
```python
from codecouncil.db.engine import create_engine, create_session_factory
import os

engine = create_engine(os.environ.get("DATABASE_URL"))
session_factory = create_session_factory(engine)
app.state.db_engine = engine
app.state.db_session_factory = session_factory
```

On shutdown:
```python
await app.state.db_engine.dispose()
```

- [ ] **Step 2: Create deps.py with get_db dependency**

```python
from typing import AsyncGenerator
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        yield session
```

- [ ] **Step 3: Verify — server starts without errors**

- [ ] **Step 4: Commit**

---

### Task 2: Replace In-Memory Routes with DB Repositories

**Files:**
- Modify: `backend/src/codecouncil/api/routes/runs.py`

Replace ALL `_runs` dict usage with repository calls. Keep `_runs` as a runtime cache for the pipeline's background task (it needs to mutate the run dict in real-time for WebSocket streaming), but on every API read, query from DB first, falling back to `_runs` for in-progress runs.

Key changes:
- `create_run`: Insert into DB via RunRepository, also keep in `_runs` for pipeline
- `list_runs`: Query DB via RunRepository, merge with any in-progress runs from `_runs`
- `get_run`: Query DB first, fall back to `_runs` for in-progress
- `delete_run`: Delete from DB AND `_runs`
- `get_events`: Query DB via EventRepository
- `get_rfc`: Query DB (rfc_content stored on run)
- `get_cost`: Calculate from DB events

- [ ] **Step 1: Add DB session dependency to all route handlers**

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from codecouncil.api.deps import get_db
from codecouncil.db.repositories import RunRepository, EventRepository, ...

@router.post("/runs", status_code=201)
async def create_run(request: CreateRunRequest, db: AsyncSession = Depends(get_db)):
    repo = RunRepository(db)
    ...
```

- [ ] **Step 2: Implement create_run with DB persistence**

Create run in DB AND keep in `_runs` for the pipeline:
```python
run_model = await repo.create_run(run_id, request.repo_url, repo_name, config_snapshot)
await db.commit()
_runs[run_id] = run  # keep for pipeline background task
```

- [ ] **Step 3: Implement list_runs from DB**

```python
@router.get("/runs")
async def list_runs(db: AsyncSession = Depends(get_db), ...):
    repo = RunRepository(db)
    db_runs = await repo.list_runs(limit=limit, offset=offset)
    # Merge with any in-progress runs from _runs that aren't in DB yet
    ...
```

- [ ] **Step 4: Implement get_run from DB with _runs fallback**

- [ ] **Step 5: Implement delete from DB + _runs**

- [ ] **Step 6: Implement get_events from EventRepository**

- [ ] **Step 7: Implement get_rfc from DB**

- [ ] **Step 8: Verify — create a run, restart server, data persists**

- [ ] **Step 9: Commit**

---

### Task 3: Pipeline Persists to DB

**Files:**
- Modify: `backend/src/codecouncil/api/pipeline.py`

The pipeline currently writes everything to the `run` dict in `_runs`. It needs to ALSO persist to DB at key checkpoints.

- [ ] **Step 1: Accept session_factory parameter in pipeline**

```python
async def run_real_council(run: dict, runs_store: dict, session_factory=None):
```

- [ ] **Step 2: Persist after ingestion phase**

```python
if session_factory:
    async with session_factory() as db:
        repo = RunRepository(db)
        await repo.update_run_status(run_id, "running", phase="analysing")
        await db.commit()
```

- [ ] **Step 3: Persist findings to DB after analysis**

```python
if session_factory:
    async with session_factory() as db:
        finding_repo = FindingRepository(db)
        for f in all_findings:
            await finding_repo.create_finding(f)
        await db.commit()
```

- [ ] **Step 4: Persist proposals after debate**

- [ ] **Step 5: Persist votes after voting**

- [ ] **Step 6: Persist events in batches (every phase completion)**

- [ ] **Step 7: Persist RFC content and final status on completion**

```python
if session_factory:
    async with session_factory() as db:
        repo = RunRepository(db)
        await repo.update_run_status(run_id, "completed", phase="done")
        await repo.update_run_cost(run_id, total_cost)
        # Store RFC content and consensus
        await db.commit()
```

- [ ] **Step 8: Pass session_factory from create_run to pipeline**

In `runs.py`:
```python
session_factory = request.app.state.db_session_factory
asyncio.create_task(run_real_council(run, _runs, session_factory=session_factory))
```

- [ ] **Step 9: Verify end-to-end — create run, wait for completion, restart server, data persists**

- [ ] **Step 10: Commit**

---

### Task 4: WebSocket Event Replay from DB

**Files:**
- Modify: `backend/src/codecouncil/api/websocket.py`

Currently the WebSocket handler reads events from `_runs`. After restart, `_runs` is empty. It should load historical events from DB.

- [ ] **Step 1: On WebSocket connect, load events from DB if not in _runs**

- [ ] **Step 2: Commit**
