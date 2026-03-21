# CodeCouncil

AI agent council for codebase intelligence. Four permanent AI agents (Archaeologist, Skeptic, Visionary, Scribe) analyse repos, debate in real time, and produce institutional-grade RFCs.

## Project Structure

- `backend/` — Python 3.12+ (FastAPI + LangGraph + SQLAlchemy async)
- `frontend/` — Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui
- `docs/` — Architecture docs, specs, plans, mockups

## Dev Commands

```bash
make install        # Install all dependencies (backend + frontend)
make dev            # Start backend + frontend + PostgreSQL + Redis via Docker Compose
make backend        # Start backend only (uvicorn with reload)
make frontend       # Start frontend only (next dev)
make db-migrate     # Run Alembic migrations
make db-reset       # Drop and recreate database
make test           # Run all tests
make test-backend   # Run backend tests only
make test-frontend  # Run frontend tests only
make lint           # Lint backend (ruff) + frontend (eslint)
make format         # Format backend (ruff format) + frontend (prettier)
make demo           # Run demo mode against a sample repo
make docker-up      # Start all services via Docker Compose
make docker-down    # Stop all services
```

## Architecture

- **Orchestration:** LangGraph state graph with 8 phases (Ingest → Analyse → Opening → Debate → Voting → Scribing → Review → Finalise)
- **Database:** PostgreSQL everywhere (SQLAlchemy async + asyncpg + Alembic)
- **Events:** EventBus fans out to PostgreSQL, WebSocket, SSE, Redis pub/sub, webhooks
- **Providers:** 7 LLM providers via official SDKs (OpenAI, Anthropic, Google, Mistral, Ollama, Bedrock, Azure)
- **Config:** 7-layer merge (defaults → global → project → runtime → env vars → API → UI)

## Agent Roster

| Agent | Handle | Color | Role |
|-------|--------|-------|------|
| The Archaeologist | archaeologist | #d4a574 | Historian, evidence collector |
| The Skeptic | skeptic | #ff6b6b | Risk analyst, challenger |
| The Visionary | visionary | #6c5ce7 | Proposal author, domain reader |
| The Scribe | scribe | #4ecdc4 | Secretary, RFC author |

## Debate Topologies

adversarial (default), collaborative, socratic, open_floor, panel, custom

## Extension Points

All use registry pattern — implement interface, register in config, auto-discovered:
- Agents: subclass `BaseAgent`
- Providers: implement `ProviderPlugin`
- Topologies: implement `DebateTopology`
- Ingestion sources: implement `IngestionSource`
- RFC renderers: implement `RFCRenderer`

## Design Principles

- Agents are permanent (memory persists across sessions)
- Multi-LLM (any agent on any provider)
- Everything is observable (structured events for all state transitions)
- RFC is a first-class institutional document
- Extensible without touching existing code
