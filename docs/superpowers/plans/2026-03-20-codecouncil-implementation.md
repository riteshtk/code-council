# CodeCouncil Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build CodeCouncil — an AI agent council for codebase intelligence with 4 permanent agents, multi-LLM support, debate topologies, real-time streaming UI, and institutional-grade RFC output.

**Architecture:** Python backend (FastAPI + LangGraph + SQLAlchemy async) with Next.js frontend. LangGraph orchestrates 8 debate phases. EventBus fans out to PostgreSQL, WebSocket, SSE, Redis, and webhooks simultaneously. All extension points (agents, providers, topologies, sources, renderers) use registry pattern for plug-and-play extensibility.

**Tech Stack:** Python 3.12+, FastAPI, LangGraph, SQLAlchemy async + asyncpg, Alembic, Pydantic v2, Typer + Rich, tree-sitter, httpx, openai/anthropic/google-generativeai/mistralai/boto3 SDKs, pytest. Next.js 15, TypeScript, Tailwind CSS v4, shadcn/ui, Zustand, React Flow. PostgreSQL 16, Redis 7, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-03-20-codecouncil-design.md`

---

## Task 1: CLAUDE.md

**Files:**
- Create: `CLAUDE.md`

- [ ] **Step 1: Create CLAUDE.md with full project context**

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "feat: add CLAUDE.md with project context and dev commands"
```

---

## Task 2: Project Scaffold

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/codecouncil/__init__.py`
- Create: `backend/src/codecouncil/main.py`
- Create: `backend/src/codecouncil/cli.py`
- Create: All `__init__.py` files for every subpackage
- Create: `backend/alembic.ini`
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`
- Create: `frontend/package.json`
- Create: `frontend/.env.example`
- Create: `Makefile`
- Create: `docker-compose.yml`
- Create: `Dockerfile.backend`
- Create: `Dockerfile.frontend`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create backend pyproject.toml**

```toml
[project]
name = "codecouncil"
version = "0.1.0"
description = "AI agent council for codebase intelligence"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "langgraph>=0.4.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "pyyaml>=6.0.2",
    "typer>=0.15.0",
    "rich>=13.9.0",
    "httpx>=0.28.0",
    "openai>=1.60.0",
    "anthropic>=0.42.0",
    "google-generativeai>=0.8.0",
    "mistralai>=1.3.0",
    "boto3>=1.36.0",
    "tiktoken>=0.8.0",
    "tree-sitter>=0.24.0",
    "tree-sitter-python>=0.23.0",
    "tree-sitter-javascript>=0.23.0",
    "tree-sitter-typescript>=0.23.0",
    "tree-sitter-go>=0.23.0",
    "tree-sitter-rust>=0.23.0",
    "tree-sitter-java>=0.23.0",
    "tree-sitter-ruby>=0.23.0",
    "redis>=5.2.0",
    "sse-starlette>=2.2.0",
    "prometheus-client>=0.21.0",
    "jinja2>=3.1.4",
    "gitpython>=3.1.44",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.25.0",
    "pytest-cov>=6.0.0",
    "respx>=0.22.0",
    "ruff>=0.8.0",
    "mypy>=1.14.0",
]

[project.scripts]
codecouncil = "codecouncil.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/codecouncil"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "SIM"]
```

- [ ] **Step 2: Create all __init__.py files and empty module stubs**

Create every directory and `__init__.py` for the full backend tree:

```
backend/src/codecouncil/__init__.py          (version = "0.1.0")
backend/src/codecouncil/main.py              (empty FastAPI app placeholder)
backend/src/codecouncil/cli.py               (empty Typer app placeholder)
backend/src/codecouncil/config/__init__.py
backend/src/codecouncil/config/schema.py
backend/src/codecouncil/config/loader.py
backend/src/codecouncil/config/defaults.py
backend/src/codecouncil/models/__init__.py
backend/src/codecouncil/models/state.py
backend/src/codecouncil/models/events.py
backend/src/codecouncil/models/findings.py
backend/src/codecouncil/models/proposals.py
backend/src/codecouncil/models/votes.py
backend/src/codecouncil/models/agents.py
backend/src/codecouncil/models/repo.py
backend/src/codecouncil/models/rfc.py
backend/src/codecouncil/events/__init__.py
backend/src/codecouncil/events/bus.py
backend/src/codecouncil/events/persistence.py
backend/src/codecouncil/events/websocket.py
backend/src/codecouncil/events/sse.py
backend/src/codecouncil/providers/__init__.py
backend/src/codecouncil/providers/base.py
backend/src/codecouncil/providers/registry.py
backend/src/codecouncil/providers/cost.py
backend/src/codecouncil/providers/openai_provider.py
backend/src/codecouncil/providers/anthropic_provider.py
backend/src/codecouncil/providers/google_provider.py
backend/src/codecouncil/providers/mistral_provider.py
backend/src/codecouncil/providers/ollama_provider.py
backend/src/codecouncil/providers/bedrock_provider.py
backend/src/codecouncil/providers/azure_provider.py
backend/src/codecouncil/ingestion/__init__.py
backend/src/codecouncil/ingestion/base.py
backend/src/codecouncil/ingestion/registry.py
backend/src/codecouncil/ingestion/github.py
backend/src/codecouncil/ingestion/gitlab.py
backend/src/codecouncil/ingestion/bitbucket.py
backend/src/codecouncil/ingestion/local.py
backend/src/codecouncil/ingestion/archive.py
backend/src/codecouncil/ingestion/context.py
backend/src/codecouncil/ingestion/analyzers/__init__.py
backend/src/codecouncil/ingestion/analyzers/churn.py
backend/src/codecouncil/ingestion/analyzers/bus_factor.py
backend/src/codecouncil/ingestion/analyzers/dead_code.py
backend/src/codecouncil/ingestion/analyzers/ast_parser.py
backend/src/codecouncil/ingestion/analyzers/dependency.py
backend/src/codecouncil/ingestion/analyzers/cve.py
backend/src/codecouncil/ingestion/analyzers/secrets.py
backend/src/codecouncil/ingestion/analyzers/licence.py
backend/src/codecouncil/ingestion/analyzers/git_history.py
backend/src/codecouncil/ingestion/analyzers/incremental.py
backend/src/codecouncil/ingestion/analyzers/test_coverage.py
backend/src/codecouncil/agents/__init__.py
backend/src/codecouncil/agents/base.py
backend/src/codecouncil/agents/registry.py
backend/src/codecouncil/agents/memory.py
backend/src/codecouncil/agents/archaeologist.py
backend/src/codecouncil/agents/skeptic.py
backend/src/codecouncil/agents/visionary.py
backend/src/codecouncil/agents/scribe.py
backend/src/codecouncil/debate/__init__.py
backend/src/codecouncil/debate/base.py
backend/src/codecouncil/debate/registry.py
backend/src/codecouncil/debate/adversarial.py
backend/src/codecouncil/debate/collaborative.py
backend/src/codecouncil/debate/socratic.py
backend/src/codecouncil/debate/open_floor.py
backend/src/codecouncil/debate/panel.py
backend/src/codecouncil/debate/custom.py
backend/src/codecouncil/graph/__init__.py
backend/src/codecouncil/graph/council_graph.py
backend/src/codecouncil/graph/nodes.py
backend/src/codecouncil/graph/checkpointing.py
backend/src/codecouncil/output/__init__.py
backend/src/codecouncil/output/base.py
backend/src/codecouncil/output/registry.py
backend/src/codecouncil/output/markdown.py
backend/src/codecouncil/output/json_renderer.py
backend/src/codecouncil/output/html.py
backend/src/codecouncil/output/templates/rfc.html.j2  (empty)
backend/src/codecouncil/output/action_items.py
backend/src/codecouncil/output/cost_report.py
backend/src/codecouncil/api/__init__.py
backend/src/codecouncil/api/app.py
backend/src/codecouncil/api/middleware.py
backend/src/codecouncil/api/websocket.py
backend/src/codecouncil/api/sse.py
backend/src/codecouncil/api/metrics.py
backend/src/codecouncil/api/routes/__init__.py
backend/src/codecouncil/api/routes/runs.py
backend/src/codecouncil/api/routes/config.py
backend/src/codecouncil/api/routes/personas.py
backend/src/codecouncil/api/routes/agents.py
backend/src/codecouncil/api/routes/providers.py
backend/src/codecouncil/api/routes/sessions.py
backend/src/codecouncil/api/routes/health.py
backend/src/codecouncil/db/__init__.py
backend/src/codecouncil/db/engine.py
backend/src/codecouncil/db/models.py
backend/src/codecouncil/db/repositories.py
backend/src/codecouncil/db/migrations/alembic/env.py   (empty)
backend/src/codecouncil/db/migrations/alembic/versions/ (empty dir)
backend/tests/__init__.py
backend/tests/unit/__init__.py
backend/tests/unit/test_config.py
backend/tests/unit/test_agents.py
backend/tests/unit/test_parsers.py
backend/tests/unit/test_topology.py
backend/tests/unit/test_providers.py
backend/tests/unit/test_ingestion.py
backend/tests/unit/test_output.py
backend/tests/integration/__init__.py
backend/tests/integration/test_graph_run.py
backend/tests/integration/test_api.py
```

Each `.py` file starts empty or with a minimal docstring. `__init__.py` is just `""`.

- [ ] **Step 3: Create backend/.env.example**

```env
# Database
DATABASE_URL=postgresql+asyncpg://codecouncil:codecouncil@localhost:5432/codecouncil

# Redis
REDIS_URL=redis://localhost:6379/0

# LLM Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=
MISTRAL_API_KEY=

# AWS Bedrock
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_DEFAULT_REGION=us-east-1

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=

# GitHub (for private repos)
GITHUB_TOKEN=
GITLAB_TOKEN=
BITBUCKET_TOKEN=

# Server
API_PORT=8000
UI_PORT=3000
```

- [ ] **Step 4: Create alembic.ini**

```ini
[alembic]
script_location = src/codecouncil/db/migrations/alembic
sqlalchemy.url = postgresql+asyncpg://codecouncil:codecouncil@localhost:5432/codecouncil

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 5: Create frontend package.json**

```json
{
  "name": "codecouncil-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\""
  },
  "dependencies": {
    "next": "^15.1.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@xyflow/react": "^12.4.0",
    "zustand": "^5.0.0",
    "lucide-react": "^0.469.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.6.0",
    "class-variance-authority": "^0.7.1"
  },
  "devDependencies": {
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.7.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "postcss": "^8.5.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.1.0",
    "prettier": "^3.4.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.1.0"
  }
}
```

- [ ] **Step 6: Create frontend/.env.example**

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

- [ ] **Step 7: Create docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: codecouncil
      POSTGRES_PASSWORD: codecouncil
      POSTGRES_DB: codecouncil
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U codecouncil"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: Dockerfile.backend
    ports:
      - "8000:8000"
    env_file:
      - .env
    environment:
      DATABASE_URL: postgresql+asyncpg://codecouncil:codecouncil@postgres:5432/codecouncil
      REDIS_URL: redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./backend/src:/app/src
      - ./output:/app/output

  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8000
      NEXT_PUBLIC_WS_URL: ws://backend:8000
    depends_on:
      - backend

volumes:
  pgdata:
```

- [ ] **Step 8: Create Dockerfile.backend**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY backend/pyproject.toml .
RUN uv pip install --system -e ".[dev]"

COPY backend/src ./src
COPY backend/alembic.ini .

EXPOSE 8000

CMD ["uvicorn", "codecouncil.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 9: Create Dockerfile.frontend**

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend/ .

EXPOSE 3000

CMD ["npm", "run", "dev"]
```

- [ ] **Step 10: Create Makefile**

```makefile
.PHONY: install dev backend frontend db-migrate db-reset test test-backend test-frontend lint format demo docker-up docker-down

install:
	cd backend && uv pip install --system -e ".[dev]"
	cd frontend && npm install

dev:
	docker compose up -d postgres redis
	@echo "Waiting for PostgreSQL..."
	@sleep 3
	cd backend && alembic upgrade head
	@make -j2 backend frontend

backend:
	cd backend && uvicorn codecouncil.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

db-migrate:
	cd backend && alembic upgrade head

db-reset:
	cd backend && alembic downgrade base && alembic upgrade head

test: test-backend test-frontend

test-backend:
	cd backend && pytest -v --cov=codecouncil

test-frontend:
	cd frontend && npx vitest run

lint:
	cd backend && ruff check src/ tests/
	cd frontend && npx next lint

format:
	cd backend && ruff format src/ tests/
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}"

demo:
	cd backend && codecouncil analyse https://github.com/tiangolo/fastapi --demo --stream

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
```

- [ ] **Step 11: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
.venv/
.mypy_cache/
.ruff_cache/
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
.next/
out/

# Environment
.env
*.env.local

# IDE
.idea/
.vscode/
*.swp

# Output
output/

# Database
*.db

# OS
.DS_Store
Thumbs.db

# Docker
pgdata/
```

- [ ] **Step 12: Create root .env.example** (same content as backend/.env.example)

- [ ] **Step 13: Create minimal main.py and cli.py placeholders**

`backend/src/codecouncil/main.py`:
```python
"""CodeCouncil API server."""

from fastapi import FastAPI

app = FastAPI(
    title="CodeCouncil",
    description="AI agent council for codebase intelligence",
    version="0.1.0",
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

`backend/src/codecouncil/cli.py`:
```python
"""CodeCouncil CLI."""

import typer

app = typer.Typer(name="codecouncil", help="AI agent council for codebase intelligence")


@app.command()
def analyse(repo: str):
    """Analyse a repository with the council."""
    typer.echo(f"Analysing {repo}...")


if __name__ == "__main__":
    app()
```

- [ ] **Step 14: Verify scaffold**

Run: `cd backend && uv pip install --system -e ".[dev]" && python -c "import codecouncil; print(codecouncil.__version__)"`
Expected: `0.1.0`

Run: `cd frontend && npm install`
Expected: success, no errors

- [ ] **Step 15: Commit**

```bash
git add -A
git commit -m "feat: project scaffold with full directory tree, pyproject.toml, package.json, Docker, Makefile"
```

---

## Task 3: Config System

**Files:**
- Create: `backend/src/codecouncil/config/schema.py` — Pydantic models for all config
- Create: `backend/src/codecouncil/config/loader.py` — 7-layer merge logic
- Create: `backend/src/codecouncil/config/defaults.py` — Default values + 4 persona prompts
- Create: `backend/config/default.yaml` — Default config file
- Test: `backend/tests/unit/test_config.py`

- [ ] **Step 1: Write failing tests for config schema validation**

```python
# backend/tests/unit/test_config.py
import pytest
from codecouncil.config.schema import (
    CouncilConfig,
    LLMConfig,
    AgentConfig,
    IngestConfig,
    OutputConfig,
    UIConfig,
    ProviderConfig,
)


def test_default_config_is_valid():
    """Default config should parse without errors."""
    config = CouncilConfig()
    assert config.council.max_rounds == 3
    assert config.council.debate_topology == "adversarial"
    assert config.llm.default_provider == "openai"
    assert config.llm.default_model == "gpt-4o"


def test_agent_config_defaults():
    """Each default agent should have correct defaults."""
    config = CouncilConfig()
    assert config.agents.archaeologist.enabled is True
    assert config.agents.archaeologist.temperature == 0.3
    assert config.agents.skeptic.temperature == 0.2
    assert config.agents.skeptic.can_deadlock is True
    assert config.agents.visionary.temperature == 0.7
    assert config.agents.visionary.max_proposals == 8
    assert config.agents.scribe.temperature == 0.1


def test_provider_inherits_default():
    """Agent with empty provider should inherit default."""
    config = CouncilConfig()
    assert config.agents.archaeologist.provider == ""
    # Resolved provider should be the default
    resolved = config.agents.archaeologist.provider or config.llm.default_provider
    assert resolved == "openai"


def test_vote_threshold_range():
    """Vote threshold must be between 0 and 1."""
    with pytest.raises(Exception):
        CouncilConfig(council={"vote_threshold": 1.5})


def test_config_from_yaml(tmp_path):
    """Config should load from YAML file."""
    from codecouncil.config.loader import load_config

    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text("""
council:
  max_rounds: 5
  debate_topology: collaborative
llm:
  default_provider: anthropic
  default_model: claude-sonnet-4-20250514
""")
    config = load_config(config_path=str(yaml_file))
    assert config.council.max_rounds == 5
    assert config.council.debate_topology == "collaborative"
    assert config.llm.default_provider == "anthropic"


def test_config_env_override(monkeypatch):
    """Environment variables should override config."""
    from codecouncil.config.loader import load_config

    monkeypatch.setenv("CC_COUNCIL__MAX_ROUNDS", "7")
    config = load_config()
    assert config.council.max_rounds == 7


def test_config_layer_precedence(tmp_path, monkeypatch):
    """Higher layers override lower layers."""
    from codecouncil.config.loader import load_config

    global_conf = tmp_path / "global.yaml"
    global_conf.write_text("council:\n  max_rounds: 2\n  debate_topology: panel\n")
    runtime_conf = tmp_path / "runtime.yaml"
    runtime_conf.write_text("council:\n  max_rounds: 10\n")

    config = load_config(
        global_path=str(global_conf),
        config_path=str(runtime_conf),
    )
    assert config.council.max_rounds == 10
    assert config.council.debate_topology == "panel"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/test_config.py -v`
Expected: FAIL (imports not found)

- [ ] **Step 3: Implement config/schema.py — all Pydantic config models**

Full Pydantic v2 models for every config section from the spec Section 6.2. Key models:
- `CouncilSettings` (name, max_rounds, debate_topology, vote_threshold, hitl, budget)
- `LLMSettings` (default_provider, default_model, providers dict)
- `ProviderConfig` (api_key, base_url, org_id, region, profile, endpoint, api_version)
- `AgentConfig` (enabled, provider, model, temperature, max_tokens, streaming, persona, vote_weight, focus_areas dict, thresholds dict, fallback_providers)
- `ArchaeologistConfig`, `SkepticConfig`, `VisionaryConfig`, `ScribeConfig` extending AgentConfig
- `AgentsSettings` (archaeologist, skeptic, visionary, scribe, custom list)
- `IngestConfig` (source, tokens, max_files, max_file_size_kb, git_log_limit, feature toggles, include_extensions, exclude_paths)
- `OutputConfig` (directory, filename_pattern, formats, save toggles, webhook_url)
- `UIConfig` (ports, theme, delays, show toggles, sound toggles, demo_mode)
- `CouncilConfig` (council, llm, agents, ingest, output, ui) — root model

All fields have defaults matching spec Section 6.2. Use `Field(ge=0, le=1)` for thresholds. Use `Literal` for enums.

- [ ] **Step 4: Implement config/defaults.py — default persona prompts**

Four persona prompt strings:
- `ARCHAEOLOGIST_PERSONA`: "You are the Archaeologist — the council's historian and evidence collector..."
- `SKEPTIC_PERSONA`: "You are the Skeptic — the council's risk analyst and challenger..."
- `VISIONARY_PERSONA`: "You are the Visionary — the council's proposal author and domain model reader..."
- `SCRIBE_PERSONA`: "You are the Scribe — the council's secretary and RFC author..."

Each persona includes the full personality description, speaking style, focus areas, and vote behavior from spec Section 2.1.

- [ ] **Step 5: Implement config/loader.py — 7-layer config merge**

```python
def load_config(
    global_path: str | None = None,
    project_path: str | None = None,
    config_path: str | None = None,
    overrides: dict | None = None,
) -> CouncilConfig:
```

Merge order:
1. Built-in defaults (from `CouncilConfig()`)
2. Global config (`~/.codecouncil/config.yaml` or `global_path`)
3. Project config (`.codecouncil.yaml` in cwd or `project_path`)
4. Runtime config (`config_path`)
5. Environment variables (`CC_` prefix, `__` as separator)
6. API overrides (`overrides` dict)

Use `deep_merge(base_dict, override_dict)` helper that recursively merges dicts.

- [ ] **Step 6: Create config/default.yaml**

Minimal default config YAML file with just the essentials (most defaults come from Pydantic).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_config.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add backend/src/codecouncil/config/ backend/tests/unit/test_config.py backend/config/
git commit -m "feat: config system with schema, 7-layer loader, defaults, and 4 persona prompts"
```

---

## Task 4: Data Models

**Files:**
- Create: `backend/src/codecouncil/models/state.py`
- Create: `backend/src/codecouncil/models/events.py`
- Create: `backend/src/codecouncil/models/findings.py`
- Create: `backend/src/codecouncil/models/proposals.py`
- Create: `backend/src/codecouncil/models/votes.py`
- Create: `backend/src/codecouncil/models/agents.py`
- Create: `backend/src/codecouncil/models/repo.py`
- Create: `backend/src/codecouncil/models/rfc.py`
- Create: `backend/src/codecouncil/models/__init__.py` (re-exports)

- [ ] **Step 1: Write failing tests for data models**

```python
# backend/tests/unit/test_models.py
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from codecouncil.models.events import Event, EventType, Phase
from codecouncil.models.findings import Finding, Severity
from codecouncil.models.proposals import Proposal, ProposalStatus
from codecouncil.models.votes import Vote, VoteType
from codecouncil.models.agents import AgentIdentity, AgentMemory, DebateRole
from codecouncil.models.repo import RepoContext, FileInfo, Commit
from codecouncil.models.state import CouncilState


def test_event_creation():
    event = Event(
        run_id=uuid4(),
        agent="skeptic",
        event_type=EventType.AGENT_SPEAKING,
        phase=Phase.DEBATING,
        content="I challenge this proposal.",
    )
    assert event.event_id is not None
    assert event.sequence == 0
    assert event.agent == "skeptic"


def test_finding_severity_ordering():
    assert Severity.CRITICAL.value > Severity.HIGH.value
    assert Severity.HIGH.value > Severity.MEDIUM.value
    assert Severity.MEDIUM.value > Severity.INFO.value


def test_proposal_lifecycle():
    p = Proposal(
        run_id=uuid4(),
        proposal_number=1,
        version=1,
        title="Extract DI module",
        goal="Reduce coupling",
        effort="L",
        author_agent="visionary",
    )
    assert p.status == ProposalStatus.PROPOSED


def test_vote_creation():
    v = Vote(
        run_id=uuid4(),
        proposal_id=uuid4(),
        agent="skeptic",
        vote=VoteType.NO,
        rationale="Migration cost too high.",
        confidence=0.9,
    )
    assert v.vote == VoteType.NO
    assert 0 <= v.confidence <= 1


def test_council_state_accumulation():
    state = CouncilState(
        run_id=uuid4(),
        repo_url="https://github.com/test/repo",
    )
    assert state.findings == []
    assert state.proposals == []
    assert state.votes == []
    assert state.phase == Phase.INGESTING


def test_agent_identity():
    identity = AgentIdentity(
        name="The Skeptic",
        handle="skeptic",
        color="#ff6b6b",
        description="Risk analyst and challenger",
        debate_role=DebateRole.CHALLENGER,
    )
    assert identity.handle == "skeptic"


def test_repo_context():
    ctx = RepoContext(
        repo_url="https://github.com/test/repo",
        repo_name="test/repo",
    )
    assert ctx.file_tree == []
    assert ctx.git_log == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/test_models.py -v`
Expected: FAIL

- [ ] **Step 3: Implement all model files**

Each model file uses Pydantic BaseModel with proper types, defaults, and validators.

Key models per file:
- `events.py`: `EventType` (30+ enum values from spec 7.2), `Phase` (8 values), `EventMetadata`, `Event`
- `findings.py`: `Severity` (IntEnum: INFO=1, MEDIUM=2, HIGH=3, CRITICAL=4), `Finding`
- `proposals.py`: `ProposalStatus` (PROPOSED, CHALLENGED, REVISED, VOTED, PASSED, FAILED, DEADLOCKED, WITHDRAWN), `Proposal`
- `votes.py`: `VoteType` (YES, NO, ABSTAIN), `Vote`
- `agents.py`: `DebateRole` (ANALYST, CHALLENGER, PROPOSER, SCRIBE, MODERATOR), `AgentIdentity`, `AgentMemory`, `AgentStatus` (ACTIVE, PAUSED, OBSERVING)
- `repo.py`: `FileInfo`, `Commit`, `ChurnReport`, `BusFactorReport`, `DeadCodeItem`, `ImportGraph`, `CircularDep`, `Dependency`, `CVEResult`, `SecretFinding`, `LicenceReport`, `TestCoverage`, `RepoStats`, `RepoContext`
- `rfc.py`: `RFCSection`, `RFC`
- `state.py`: `CouncilState` (the LangGraph state — run_id, repo_url, config, phase, repo_context, findings, proposals, votes, debate_rounds, rfc_content, agent_memories, events, cost_total)

- [ ] **Step 4: Update models/__init__.py with re-exports**

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_models.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add backend/src/codecouncil/models/ backend/tests/unit/test_models.py
git commit -m "feat: all Pydantic data models (events, findings, proposals, votes, agents, repo, rfc, state)"
```

---

## Task 5: Database Foundation

**Files:**
- Create: `backend/src/codecouncil/db/engine.py`
- Create: `backend/src/codecouncil/db/models.py` — SQLAlchemy ORM models
- Create: `backend/src/codecouncil/db/repositories.py` — Data access layer
- Create: `backend/src/codecouncil/db/migrations/alembic/env.py`
- Create: Initial Alembic migration

- [ ] **Step 1: Implement db/engine.py — async engine setup**

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from codecouncil.config.loader import load_config

def create_engine(database_url: str | None = None):
    url = database_url or "postgresql+asyncpg://codecouncil:codecouncil@localhost:5432/codecouncil"
    engine = create_async_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_recycle=300,
        pool_pre_ping=True,
        echo=False,
    )
    return engine

def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 2: Implement db/models.py — all ORM table models**

SQLAlchemy 2.0 declarative models for all 8 tables from spec Section 11:
- `RunModel` (runs table)
- `EventModel` (events table — indexed on run_id + sequence)
- `FindingModel` (findings table)
- `ProposalModel` (proposals table)
- `VoteModel` (votes table)
- `SessionModel` (sessions table)
- `AgentMemoryModel` (agent_memories table)
- `PersonaModel` (personas table)

All UUIDs as primary keys. All timestamps as `DateTime(timezone=True)` defaulting to `func.now()`. JSON columns for `structured` and `config_snapshot`. Array columns for `runs` in sessions.

- [ ] **Step 3: Implement db/repositories.py — data access layer**

Async repository methods:
- `RunRepository`: create_run, get_run, list_runs, update_run_status, update_run_cost, delete_run
- `EventRepository`: create_event, get_events_for_run (paginated, filterable by agent/type/phase), get_events_after_sequence
- `FindingRepository`: create_finding, get_findings_for_run
- `ProposalRepository`: create_proposal, get_proposals_for_run, update_proposal_status
- `VoteRepository`: create_vote, get_votes_for_run, get_votes_for_proposal
- `SessionRepository`: create_session, get_session, list_sessions
- `AgentMemoryRepository`: get_memory, save_memory, clear_memory
- `PersonaRepository`: CRUD for personas

- [ ] **Step 4: Implement Alembic env.py**

Configure async Alembic with the SQLAlchemy models. Import all ORM models so Alembic can auto-detect them.

- [ ] **Step 5: Generate initial migration**

Run: `cd backend && alembic revision --autogenerate -m "initial tables"`
Verify: migration file created with all 8 tables

- [ ] **Step 6: Test migration against local PostgreSQL**

Run: `docker compose up -d postgres && cd backend && alembic upgrade head`
Expected: all tables created

Run: `cd backend && alembic downgrade base && alembic upgrade head`
Expected: clean round-trip

- [ ] **Step 7: Commit**

```bash
git add backend/src/codecouncil/db/ backend/alembic.ini
git commit -m "feat: database foundation — SQLAlchemy ORM models, repositories, Alembic migration"
```

---

## Task 6: Event System

**Files:**
- Create: `backend/src/codecouncil/events/bus.py`
- Create: `backend/src/codecouncil/events/persistence.py`
- Create: `backend/src/codecouncil/events/websocket.py`
- Create: `backend/src/codecouncil/events/sse.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/unit/test_events.py
import pytest
import asyncio
from uuid import uuid4
from codecouncil.events.bus import EventBus
from codecouncil.models.events import Event, EventType, Phase


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_emit():
    bus = EventBus()
    run_id = uuid4()
    received = []

    async def collector():
        async for event in bus.subscribe(run_id):
            received.append(event)
            if len(received) >= 2:
                break

    event1 = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Run started")
    event2 = Event(run_id=run_id, agent="archaeologist", event_type=EventType.AGENT_ACTIVATED, phase=Phase.ANALYSING, content="Activated")

    task = asyncio.create_task(collector())
    await asyncio.sleep(0.01)
    await bus.emit(event1)
    await bus.emit(event2)
    await task

    assert len(received) == 2
    assert received[0].event_type == EventType.RUN_STARTED
    assert received[1].agent == "archaeologist"


@pytest.mark.asyncio
async def test_event_sequence_auto_increments():
    bus = EventBus()
    run_id = uuid4()

    e1 = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Start")
    e2 = Event(run_id=run_id, agent="system", event_type=EventType.PHASE_STARTED, phase=Phase.ANALYSING, content="Analyse")

    await bus.emit(e1)
    await bus.emit(e2)

    assert e1.sequence == 1
    assert e2.sequence == 2


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = EventBus()
    run_id = uuid4()
    received_a, received_b = [], []

    async def sub_a():
        async for event in bus.subscribe(run_id):
            received_a.append(event)
            if len(received_a) >= 1:
                break

    async def sub_b():
        async for event in bus.subscribe(run_id):
            received_b.append(event)
            if len(received_b) >= 1:
                break

    task_a = asyncio.create_task(sub_a())
    task_b = asyncio.create_task(sub_b())
    await asyncio.sleep(0.01)

    event = Event(run_id=run_id, agent="system", event_type=EventType.RUN_STARTED, phase=Phase.INGESTING, content="Start")
    await bus.emit(event)

    await task_a
    await task_b
    assert len(received_a) == 1
    assert len(received_b) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/unit/test_events.py -v`
Expected: FAIL

- [ ] **Step 3: Implement events/bus.py — EventBus**

Core EventBus with:
- `asyncio.Queue` per subscriber per run_id
- `emit(event)` — assigns sequence number, fans out to all subscribers + registered handlers
- `subscribe(run_id)` — returns AsyncIterator[Event]
- `replay(run_id, after_sequence)` — replays from persistence
- Handler registration: `add_handler(handler_fn)` for persistence, WebSocket, SSE, Redis, webhook
- Thread-safe sequence counter per run_id

- [ ] **Step 4: Implement events/persistence.py**

`EventPersistenceHandler` — receives events from bus, writes to PostgreSQL via EventRepository.

- [ ] **Step 5: Implement events/websocket.py**

`WebSocketPublisher` — manages set of connected WebSocket clients per run_id. On event: serialize and send to all clients. Handles client disconnect gracefully.

- [ ] **Step 6: Implement events/sse.py**

`SSEPublisher` — similar to WebSocket but for SSE. Uses `sse-starlette` format. Supports `Last-Event-ID` for reconnect.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_events.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add backend/src/codecouncil/events/ backend/tests/unit/test_events.py
git commit -m "feat: event system — EventBus with fan-out to DB, WebSocket, SSE"
```

---

## Task 7: Provider System

**Files:**
- Create: `backend/src/codecouncil/providers/base.py`
- Create: `backend/src/codecouncil/providers/registry.py`
- Create: `backend/src/codecouncil/providers/cost.py`
- Create: 7 provider implementations
- Test: `backend/tests/unit/test_providers.py`

- [ ] **Step 1: Write failing tests for provider interface and registry**

Test: provider registry lookup, fallback chain execution, cost tracking accumulation, token counting. Use mock providers for unit tests.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement providers/base.py — ProviderPlugin ABC**

Abstract base class with: `stream()`, `complete()`, `count_tokens()`, `supports_streaming()`, `max_context_tokens()`. Plus `Message` dataclass (role, content).

- [ ] **Step 4: Implement providers/registry.py**

`ProviderRegistry`: register provider by name, get by name, list all, resolve fallback chain (try primary → fallback list → raise), auto-discover from subclasses.

- [ ] **Step 5: Implement providers/cost.py**

`CostTracker`: pricing table dict (provider → model → {input_per_1k, output_per_1k}), `record_call()`, `get_run_cost()`, `get_agent_breakdown()`, `check_budget()`. Pricing for all models from all 7 providers.

- [ ] **Step 6: Implement all 7 providers**

Each provider file implements ProviderPlugin:
- `openai_provider.py` — uses `openai` SDK, `tiktoken` for counting
- `anthropic_provider.py` — uses `anthropic` SDK, prompt caching support (cache_control on system + RepoContext messages)
- `google_provider.py` — uses `google.generativeai`
- `mistral_provider.py` — uses `mistralai`
- `ollama_provider.py` — uses `openai` SDK with `base_url=http://localhost:11434/v1`
- `bedrock_provider.py` — uses `boto3` `bedrock-runtime` client, `invoke_model_with_response_stream`
- `azure_provider.py` — uses `openai` SDK with Azure `base_url` + `api_version`

All implement streaming via `async for` over provider's stream response. All handle timeouts (default 120s), retries (3 attempts, exponential backoff).

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_providers.py -v`
Expected: all PASS

- [ ] **Step 8: Commit**

```bash
git add backend/src/codecouncil/providers/ backend/tests/unit/test_providers.py
git commit -m "feat: provider system — 7 LLM providers, fallback chains, cost tracking"
```

---

## Task 8: Ingestion System

**Files:**
- Create: `backend/src/codecouncil/ingestion/base.py`
- Create: `backend/src/codecouncil/ingestion/registry.py`
- Create: 5 source adapters (github, gitlab, bitbucket, local, archive)
- Create: `backend/src/codecouncil/ingestion/context.py`
- Create: 11 analyzers in `analyzers/`
- Test: `backend/tests/unit/test_ingestion.py`

- [ ] **Step 1: Write failing tests for ingestion**

Test: local source adapter (scan a temp directory), churn calculator (given mock git log), bus factor calculator, dead code detection (given mock import graph), dependency parser (given mock package.json), secret detection (given strings with fake API keys), incremental diffing.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement ingestion/base.py — IngestionSource ABC**

```python
class IngestionSource(ABC):
    @abstractmethod
    def can_handle(self, url: str) -> bool: ...
    @abstractmethod
    async def ingest(self, url: str, config: IngestConfig) -> RepoContext: ...
```

- [ ] **Step 4: Implement ingestion/registry.py**

Auto-detect source from URL pattern or config.ingest.source.

- [ ] **Step 5: Implement all 5 source adapters**

- `github.py`: GitHub REST API (file tree, contents) + `git clone` for history. Token auth from config.
- `gitlab.py`: GitLab REST API + clone.
- `bitbucket.py`: Bitbucket REST API + clone.
- `local.py`: Direct filesystem scan. `git log` via GitPython if `.git` present.
- `archive.py`: Extract .zip/.tar.gz to temp dir, delegate to local adapter.

All adapters: respect `max_files`, `max_file_size_kb`, `include_extensions`, `exclude_paths` from config.

- [ ] **Step 6: Implement all 11 analyzers**

Each analyzer is an async function that takes relevant input and returns its report model:

- `git_history.py`: Parse git log via GitPython → list[Commit], per-file author map, branch topology, commit sentiment (keyword lists: urgent/fix/hotfix/bug = negative, feat/add/improve = positive, else neutral)
- `churn.py`: Given git history + config window (default 90 days) → per-file churn rate. Flag files above threshold.
- `bus_factor.py`: Given per-file author map → per-module author count. Flag modules below threshold.
- `dead_code.py`: Given import graph → find functions/modules with zero inbound references. Exclude test files from consumers (test-only usage = still dead).
- `ast_parser.py`: Tree-sitter for 8 languages. Parse each file → function/class inventory (name, line start, line count). Build import graph (who imports whom). Detect circular dependencies. Calculate LOC + basic complexity (nesting depth).
- `dependency.py`: Parse pyproject.toml (toml stdlib), package.json (json), go.mod (regex), Cargo.toml (toml), pom.xml (xml.etree), Gemfile (regex) → list[Dependency] with name, current version, latest version (via PyPI/npm/etc API calls).
- `cve.py`: POST to `https://api.osv.dev/v1/querybatch` with package list → CVEResult per package.
- `secrets.py`: Regex patterns for: AWS access keys (`AKIA...`), generic API keys (`[A-Za-z0-9]{32,}`), passwords in strings (`password\s*=\s*["']`), bearer tokens, .env files in git. SHA-256 hash each match. Return hash + file + line.
- `licence.py`: Detect LICENSE file → identify type (MIT, Apache, GPL, BSD, etc. by content patterns). Check dependency licences. Flag GPL dependencies in non-GPL projects.
- `test_coverage.py`: Find test files (files matching `test_*.py`, `*_test.go`, `*.test.ts`, etc.). Compute ratio test files / source files. Parse `.coverage` (sqlite) or `lcov.info` if present.
- `incremental.py`: SHA-256 hash per file. Store/load from DB. Diff against previous run. Return changed file list.

- [ ] **Step 7: Implement ingestion/context.py — RepoContext builder**

Orchestrates: call source adapter → run all analyzers in parallel (asyncio.gather) → assemble RepoContext.

- [ ] **Step 8: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_ingestion.py -v`
Expected: all PASS

- [ ] **Step 9: Commit**

```bash
git add backend/src/codecouncil/ingestion/ backend/tests/unit/test_ingestion.py
git commit -m "feat: ingestion system — 5 source adapters, 11 analyzers, incremental diffing"
```

---

## Task 9: Agent System

**Files:**
- Create: `backend/src/codecouncil/agents/base.py`
- Create: `backend/src/codecouncil/agents/registry.py`
- Create: `backend/src/codecouncil/agents/memory.py`
- Create: 4 agent files (archaeologist, skeptic, visionary, scribe)
- Test: `backend/tests/unit/test_agents.py`

- [ ] **Step 1: Write failing tests**

Test: agent registration, agent analyze method (with mocked provider), structured output parsing (extract findings/proposals from text with markers), memory load/save/summarize, cross-agent addressing in speak method.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement agents/base.py — BaseAgent**

```python
class BaseAgent(ABC):
    identity: AgentIdentity
    config: AgentConfig
    memory: AgentMemory | None
    provider: ProviderPlugin
    event_bus: EventBus

    async def analyze(self, state: CouncilState) -> list[Finding]
    async def speak(self, state: CouncilState, context: DebateContext) -> AgentResponse
    async def vote(self, proposal: Proposal, state: CouncilState) -> Vote
    async def update_memory(self, state: CouncilState) -> None

    # Shared helpers
    async def _call_llm(self, messages: list[Message]) -> AsyncIterator[str]
    def _parse_findings(self, text: str) -> list[Finding]
    def _parse_proposals(self, text: str) -> list[Proposal]
    def _parse_vote(self, text: str) -> Vote
    def _build_system_prompt(self) -> str
    def _build_context_prompt(self, state: CouncilState) -> str
```

`DebateContext` dataclass: current_round, max_rounds, active_proposal, addressed_by, debate_history, addressing_agent.

`AgentResponse` dataclass: content (full text), findings (parsed), proposals (parsed), addressing (agent handle if addressing someone).

Streaming: `_call_llm` yields tokens, emits `agent_thinking` and `agent_speaking` events via EventBus. As markers are parsed from the stream (`[FINDING:CRITICAL]`, `[PROPOSAL]`), emit `finding_emitted` and `proposal_created` events in real-time.

- [ ] **Step 4: Implement agents/registry.py**

Auto-discover all BaseAgent subclasses. Register by handle. Support custom agents from `agents.custom` config. Scan `~/.codecouncil/plugins/` for plugin agents.

- [ ] **Step 5: Implement agents/memory.py**

`AgentMemoryManager`:
- `load_memory(agent_handle)` → AgentMemory (from DB)
- `save_memory(agent_handle, session_summary)` → persist to DB
- `summarize_session(agent_handle, state: CouncilState)` → use agent's LLM to compress session into summary
- `get_priors(agent_handle)` → list of past observations for prompt injection
- `prune_old_entries(agent_handle, max_tokens)` → drop oldest entries if over limit

- [ ] **Step 6: Implement archaeologist.py**

Persona from defaults. Focus areas: churn_rate, bus_factor, dead_code, todo_accumulation, commit_sentiment, file_age, author_concentration, rewrite_frequency.

`analyze()`: Build prompt with RepoContext data relevant to focus areas. Call LLM. Parse findings with severity.

`speak()`: Present findings declaratively. Reference specific files, commits, numbers. No recommendations.

`vote()`: Vote based on historical precedent. If proposal contradicts patterns seen in this codebase's history, vote NO.

- [ ] **Step 7: Implement skeptic.py**

Focus areas: security_surface, coupling, cve_scan, test_coverage, api_contracts, performance, hidden_deps, blast_radius.

Special: `can_deadlock=True`. `declare_deadlock(proposal, evidence)` method.

`speak()`: Address other agents by name. Follow implications. Never partially concede.

`vote()`: Default NO with rationale. Concede only when fully convinced (high confidence threshold).

- [ ] **Step 8: Implement visionary.py**

Focus areas: ddd_patterns, refactor_paths, design_patterns, bounded_contexts, module_boundaries, architecture_evolution.

`analyze()`: Read code for what it wants to become. Identify refactor opportunities.

`speak()`: Create proposals with title, goal, effort estimate, breaking change flag. Can revise proposals mid-debate. Can withdraw proposals.

`vote()`: YES on own proposals unless Skeptic has convincing evidence. Can change mind on record.

- [ ] **Step 9: Implement scribe.py**

Focus: synthesis only. Does not generate findings or proposals.

`analyze()`: Returns empty findings list (Scribe observes only).

`speak()`: Summarize current state of debate. Preserve exact quotes from other agents. Note disagreements without smoothing.

`vote()`: Does not vote on proposals. Only votes on RFC completeness.

`synthesize_rfc(state: CouncilState) -> RFC`: The Scribe's main job. Build full RFC from state: header, executive summary, findings, proposals with votes, deadlocked items, action items, debate appendix, cost summary.

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_agents.py -v`
Expected: all PASS

- [ ] **Step 11: Commit**

```bash
git add backend/src/codecouncil/agents/ backend/tests/unit/test_agents.py
git commit -m "feat: agent system — BaseAgent, 4 default agents, streaming, memory, structured parsing"
```

---

## Task 10: Debate Topologies

**Files:**
- Create: `backend/src/codecouncil/debate/base.py`
- Create: `backend/src/codecouncil/debate/registry.py`
- Create: 6 topology files
- Test: `backend/tests/unit/test_topology.py`

- [ ] **Step 1: Write failing tests**

Test: adversarial turn order (Visionary → Skeptic → Visionary → Others → Skeptic), collaborative consensus requirement, panel fixed rotation, custom YAML parsing and step execution, deadlock declaration.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement debate/base.py — DebateTopology ABC**

```python
class DebateTopology(ABC):
    @abstractmethod
    def get_turn_order(self, state: CouncilState) -> list[AgentTurn]: ...
    @abstractmethod
    def can_interrupt(self, agent: str, current_speaker: str) -> bool: ...
    @abstractmethod
    def should_end_round(self, state: CouncilState, round_num: int) -> bool: ...
    @abstractmethod
    def get_next_speaker(self, state: CouncilState, last_turn: AgentTurn) -> str | None: ...
    def on_deadlock(self, proposal: Proposal, agent: str, evidence: str) -> None: ...
```

`AgentTurn` dataclass: agent_handle, action (present/challenge/respond/propose/vote), target_agent, target_proposal.

- [ ] **Step 4: Implement debate/registry.py**

Register topologies by string key. Look up from config.council.debate_topology.

- [ ] **Step 5: Implement all 6 topologies**

- `adversarial.py`: For each proposal → Visionary presents → Skeptic challenges → Visionary responds → Others weigh in → Skeptic final word. Skeptic can deadlock anytime.
- `collaborative.py`: Arch → Visionary → Skeptic (must propose mitigations) → consensus check. No agent can vote NO without proposing alternative.
- `socratic.py`: Engine generates questions for each agent in turn. Agents speak only when questioned. Engine synthesizes after all questioned.
- `open_floor.py`: Any agent can respond to any other. Max 1 response per agent per round. Auto-timer or max responses ends round.
- `panel.py`: Fixed rotation: Arch → Skeptic → Visionary → others. One proposal per round. No interruptions. Vote immediately after.
- `custom.py`: Parse YAML step array. Each step: {agent, action, target?, condition?}. Support conditionals (simple expression eval). Execute steps in order.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd backend && pytest tests/unit/test_topology.py -v`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/codecouncil/debate/ backend/tests/unit/test_topology.py
git commit -m "feat: debate topologies — adversarial, collaborative, socratic, open_floor, panel, custom"
```

---

## Task 11: LangGraph Graph

**Files:**
- Create: `backend/src/codecouncil/graph/council_graph.py`
- Create: `backend/src/codecouncil/graph/nodes.py`
- Create: `backend/src/codecouncil/graph/checkpointing.py`
- Test: `backend/tests/integration/test_graph_run.py`

- [ ] **Step 1: Write failing integration test**

Test: full graph run with mock providers. Submit a small mock RepoContext. Verify all phases execute in order. Verify events emitted. Verify RFC produced. Verify proposals have votes.

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Implement graph/nodes.py — all graph node functions**

Each node is an async function that takes `CouncilState` and returns updated state:

- `ingest_node(state)`: Call ingestion system → set state.repo_context, emit ingest events
- `analyse_node(state)`: Fan-out via asyncio.gather → all analyst agents run analyze() in parallel → collect findings → set state.findings
- `opening_node(state)`: Sequential → each agent calls speak() with findings context → emit events
- `debate_node(state)`: Get topology → loop rounds. Each round: get_next_speaker → agent.speak() → parse response → update proposals → emit events. Check should_end_round.
- `voting_node(state)`: For each proposal → each voting agent calls vote() → collect votes → determine PASSED/FAILED/DEADLOCKED → emit vote events
- `scribing_node(state)`: Scribe agent synthesizes RFC → set state.rfc_content → emit rfc events
- `review_node(state)`: If hitl_enabled → interrupt graph (LangGraph interrupt mechanism) → wait for human input → process challenges/overrides → resume
- `finalise_node(state)`: Save RFC to file + DB → update agent memories → emit run_completed → return final state

- [ ] **Step 4: Implement graph/council_graph.py — LangGraph StateGraph**

```python
from langgraph.graph import StateGraph, END

def build_council_graph(config: CouncilConfig) -> StateGraph:
    graph = StateGraph(CouncilState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("analyse", analyse_node)
    graph.add_node("opening", opening_node)
    graph.add_node("debate", debate_node)
    graph.add_node("voting", voting_node)
    graph.add_node("scribing", scribing_node)
    graph.add_node("review", review_node)
    graph.add_node("finalise", finalise_node)

    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "analyse")
    graph.add_edge("analyse", "opening")
    graph.add_edge("opening", "debate")

    # Conditional: debate may loop
    graph.add_conditional_edges("debate", should_continue_debate, {
        "continue": "debate",
        "vote": "voting",
    })

    graph.add_edge("voting", "scribing")

    # Conditional: HITL review
    graph.add_conditional_edges("scribing", should_review, {
        "review": "review",
        "finalise": "finalise",
    })

    # Review can loop back to debate or finalise
    graph.add_conditional_edges("review", review_decision, {
        "redebate": "debate",
        "finalise": "finalise",
    })

    graph.add_edge("finalise", END)

    return graph.compile(checkpointer=PostgresCheckpointer())
```

- [ ] **Step 5: Implement graph/checkpointing.py**

PostgreSQL-backed checkpointer for LangGraph. Saves state after each node. Supports resume from any checkpoint.

- [ ] **Step 6: Run integration test**

Run: `cd backend && pytest tests/integration/test_graph_run.py -v`
Expected: PASS (with mock providers)

- [ ] **Step 7: Commit**

```bash
git add backend/src/codecouncil/graph/ backend/tests/integration/test_graph_run.py
git commit -m "feat: LangGraph council graph — 8 nodes, conditional edges, checkpointing, HITL"
```

---

## Task 12: Output System

**Files:**
- Create: `backend/src/codecouncil/output/base.py`
- Create: `backend/src/codecouncil/output/registry.py`
- Create: `backend/src/codecouncil/output/markdown.py`
- Create: `backend/src/codecouncil/output/json_renderer.py`
- Create: `backend/src/codecouncil/output/html.py`
- Create: `backend/src/codecouncil/output/templates/rfc.html.j2`
- Create: `backend/src/codecouncil/output/action_items.py`
- Create: `backend/src/codecouncil/output/cost_report.py`
- Test: `backend/tests/unit/test_output.py`

- [ ] **Step 1: Write failing tests**

Test: markdown renderer produces valid markdown with all sections, JSON renderer produces valid JSON, action item extractor finds items from proposals, cost report calculates correctly.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement output/base.py — RFCRenderer ABC**

```python
class RFCRenderer(ABC):
    @abstractmethod
    def render(self, state: CouncilState) -> str: ...
    @abstractmethod
    def format_key(self) -> str: ...
```

- [ ] **Step 4: Implement output/registry.py**

- [ ] **Step 5: Implement markdown.py**

Render full RFC as Markdown matching the RFC Viewer mockup structure:
- Header (repo, date, agents, consensus, cost)
- Executive summary
- Critical findings (sorted by severity)
- Proposals with vote matrix (agent → YES/NO/ABSTAIN with confidence)
- Dissent blocks (any NO vote rationale preserved verbatim)
- Deadlocked items (both positions side by side)
- Action items (numbered, with effort + source proposal)
- Human review notes (if any)
- Debate appendix (key exchanges, configurable max)
- Cost summary table

- [ ] **Step 6: Implement json_renderer.py**

Serialize CouncilState to structured JSON with all sections.

- [ ] **Step 7: Implement html.py + rfc.html.j2**

Jinja2 template matching RFC Viewer mockup styling. Self-contained HTML (inline CSS). Print-friendly for PDF export.

- [ ] **Step 8: Implement action_items.py**

Extract action items from passed proposals. Each action item: title (from proposal), effort, source proposal ID, breaking change flag.

- [ ] **Step 9: Implement cost_report.py**

Generate per-agent cost breakdown: provider, model, input tokens, output tokens, cost USD, latency. Plus totals.

- [ ] **Step 10: Run tests to verify they pass**

- [ ] **Step 11: Commit**

```bash
git add backend/src/codecouncil/output/ backend/tests/unit/test_output.py
git commit -m "feat: output system — markdown/JSON/HTML RFC renderers, action items, cost report"
```

---

## Task 13: API Server

**Files:**
- Create: `backend/src/codecouncil/api/app.py`
- Create: `backend/src/codecouncil/api/middleware.py`
- Create: All route files in `api/routes/`
- Create: `backend/src/codecouncil/api/websocket.py`
- Create: `backend/src/codecouncil/api/sse.py`
- Create: `backend/src/codecouncil/api/metrics.py`
- Test: `backend/tests/integration/test_api.py`

- [ ] **Step 1: Write failing tests**

Test: POST /api/runs creates a run, GET /api/runs lists runs, GET /api/runs/{id} returns run, GET /api/health returns ok, GET /api/config returns config with masked secrets, POST /api/config/validate validates YAML.

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement api/app.py — FastAPI app factory**

```python
def create_app(config: CouncilConfig | None = None) -> FastAPI:
    app = FastAPI(title="CodeCouncil", version="0.1.0")
    # Register middleware
    # Register routes
    # Setup lifespan (DB engine, EventBus, etc.)
    return app
```

- [ ] **Step 4: Implement api/middleware.py**

CORS (configurable origins), rate limiting (100 req/min per IP via simple in-memory counter), structured JSON request logging (run_id on every log line), error handler (return JSON errors).

- [ ] **Step 5: Implement all route files**

Per spec Section 8.1:
- `routes/runs.py`: POST /api/runs (validate config, create Run in DB, launch graph as background task via asyncio.create_task, return run_id). GET /api/runs (paginated). GET /api/runs/{id}. DELETE /api/runs/{id} (set cancellation flag). POST /api/runs/{id}/review. GET /api/runs/{id}/rfc (content-negotiated). GET /api/runs/{id}/events (paginated, filterable). GET /api/runs/{id}/cost. POST /api/runs/{id}/rerun.
- `routes/config.py`: GET /api/config (mask secrets), POST /api/config/validate, PATCH /api/config.
- `routes/personas.py`: CRUD for personas.
- `routes/agents.py`: GET /api/agents, GET /api/agents/{handle}/memory, DELETE /api/agents/{handle}/memory.
- `routes/providers.py`: GET /api/providers (list + status), POST /api/providers/test (send a ping to provider).
- `routes/sessions.py`: GET /api/sessions, GET /api/sessions/{id}, GET /api/sessions/compare.
- `routes/health.py`: GET /api/health (DB connectivity, provider status, Redis status).

- [ ] **Step 6: Implement api/websocket.py**

WebSocket endpoint: `WS /ws/runs/{run_id}/debate`.
On connect: replay all historical events. Then stream new events. Handle human_challenge messages from client. Ping every 15s, close if no pong in 10s. On run_completed: send event, close.

- [ ] **Step 7: Implement api/sse.py**

SSE endpoint: `GET /api/runs/{id}/stream`. Same events as WebSocket. Support Last-Event-ID.

- [ ] **Step 8: Implement api/metrics.py**

Prometheus endpoint at `/metrics`. Counters/gauges/histograms per spec Section 13.

- [ ] **Step 9: Update main.py to use app factory**

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd backend && pytest tests/integration/test_api.py -v`
Expected: all PASS

- [ ] **Step 11: Commit**

```bash
git add backend/src/codecouncil/api/ backend/src/codecouncil/main.py backend/tests/integration/test_api.py
git commit -m "feat: API server — all REST routes, WebSocket, SSE, middleware, health, metrics"
```

---

## Task 14: CLI

**Files:**
- Modify: `backend/src/codecouncil/cli.py` — full CLI implementation
- Test: manual testing (CLI is hard to unit test, test via API integration)

- [ ] **Step 1: Implement full CLI with Typer + Rich**

All commands from spec Section 10:

```python
app = typer.Typer()

@app.command()
def analyse(repo, --provider, --model, --rounds, --topology, --no-skeptic, --no-visionary, --only-archaeologist, --config, --output, --format, --stream, --hitl, --budget, --demo, --open, --dry-run)

@app.command()
def serve(--api-port, --ui-port, --no-ui)

# Subcommand groups
sessions_app = typer.Typer()
app.add_typer(sessions_app, name="sessions")
# sessions list, show, compare

agents_app = typer.Typer()
app.add_typer(agents_app, name="agents")
# agents list, memory show, memory clear

personas_app = typer.Typer()
app.add_typer(personas_app, name="personas")
# personas list, add, edit, remove

providers_app = typer.Typer()
app.add_typer(providers_app, name="providers")
# providers list, test

config_app = typer.Typer()
app.add_typer(config_app, name="config")
# config show, validate, set
```

- [ ] **Step 2: Implement Rich terminal UI for `analyse --stream`**

Use Rich Live, Columns, Panel, Table:
- 4 agent panels (Columns when terminal wide enough)
- Color-coded by agent color
- Live debate feed with scroll
- Vote matrix as Table
- Cost meter in header
- RFC printed with syntax highlighting when done

- [ ] **Step 3: Implement `serve` command**

Start Uvicorn programmatically. Optionally start frontend dev server.

- [ ] **Step 4: Test CLI manually**

Run: `cd backend && codecouncil --help`
Expected: all commands listed

Run: `cd backend && codecouncil config show`
Expected: config printed

- [ ] **Step 5: Commit**

```bash
git add backend/src/codecouncil/cli.py
git commit -m "feat: CLI — all commands with Rich terminal UI, streaming debate feed, vote matrix"
```

---

## Task 15: React UI

**Files:**
- Create: All frontend source files under `frontend/src/`
- This is the largest task — broken into sub-steps by page

- [ ] **Step 1: Initialize Next.js project with Tailwind + shadcn/ui**

Run: `cd frontend && npx shadcn@latest init`
Configure: TypeScript, Tailwind CSS, App Router, src/ directory.
Install shadcn components: button, input, select, card, badge, table, tabs, skeleton, dialog, toast, toggle, separator, scroll-area, tooltip.

Set up dark theme matching mockup colors as CSS custom properties in globals.css.

- [ ] **Step 2: Create shared types (frontend/src/lib/types.ts)**

TypeScript interfaces matching all backend Pydantic models: Event, EventType, Phase, Finding, Severity, Proposal, ProposalStatus, Vote, VoteType, AgentIdentity, RunSummary, CouncilConfig, RepoContext, RFC.

- [ ] **Step 3: Create API client (frontend/src/lib/api.ts)**

Functions for all REST endpoints: createRun, getRun, listRuns, deleteRun, submitReview, getRFC, getEvents, getCost, rerun, getConfig, validateConfig, updateConfig, listPersonas, CRUD personas, listAgents, getAgentMemory, clearAgentMemory, listProviders, testProvider, listSessions, getSession, compareSessions, health.

All use `fetch` with `NEXT_PUBLIC_API_URL` base.

- [ ] **Step 4: Create WebSocket manager (frontend/src/stores/websocketManager.ts)**

Connect to `WS /ws/runs/{run_id}/debate`. Handle:
- On connect: receive historical event replay
- Stream new events → push to Zustand store
- Send human challenges
- Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s max)
- On reconnect: send `last_sequence` → server replays missed events
- Ping/pong handling
- Connection state: connecting, connected, disconnected, reconnecting

- [ ] **Step 5: Create Zustand stores**

`runStore.ts`: Current run state (run_id, phase, events, findings, proposals, votes, agents, cost). Actions: addEvent (processes incoming events and updates derived state), setRun, clearRun.

`configStore.ts`: Config state. Actions: loadConfig, updateConfig, validateConfig.

- [ ] **Step 6: Create shared components**

- `TopBar.tsx`: Logo, nav links (Home, Sessions, Config), active state
- `Skeleton.tsx`: Reusable skeleton screens
- `ErrorBoundary.tsx`: Catch and display errors

- [ ] **Step 7: Create Home page (frontend/src/app/page.tsx)**

Match mockup `01-home.html`:
- `RepoInput.tsx`: URL input with validation, source selector tabs
- `QuickConfig.tsx`: Provider, topology, rounds, agent toggles, HITL, budget chips
- `RecentRuns.tsx`: Grid of recent runs with status pills, consensus bars, cost
- `CouncilHealth.tsx`: Agent readiness + provider connectivity panel
- Stats row: total analyses, avg consensus, total spend

Form submission → POST /api/runs → redirect to /debate/[runId]

- [ ] **Step 8: Create Debate page — Agent Panels**

Match mockup `02-debate.html` left section:
- `AgentPanel.tsx`: Avatar with pulse animation (CSS @keyframes), name, status label, streaming text area with typing cursor, finding/proposal chips, mini vote record
- 4 panels stacked vertically, color-coded by agent
- Active agent has glowing border + pulse ring on avatar

- [ ] **Step 9: Create Debate page — Debate Feed**

Center section:
- `DebateFeed.tsx`: Chronological event stream. Each event: color bar (agent color), agent name, event type badge, content, timestamp. Search bar + filter buttons (All, Findings, Proposals, Challenges, Votes). Auto-scroll locked to bottom unless user scrolls up. Distinct visual treatments per event type (challenge: red tint, proposal: purple tint, revision: yellow tint, deadlock: full-width red banner).

- [ ] **Step 10: Create Debate page — Graph Visualizer**

Right section:
- `GraphVisualizer.tsx`: React Flow with custom nodes for each phase (Ingest, Analyse, Opening, Debate, Voting, Scribing, Review, Done). Active node glows. Completed nodes show checkmark. Edges light up on transition. Clickable nodes show events from that phase. Collapse button.

- [ ] **Step 11: Create Debate page — Proposal Tracker + Vote Reveal**

Bottom section:
- `ProposalTracker.tsx`: Card per proposal. Status badge, vote tally dots, effort badge. Cards animate between states.
- `VoteReveal.tsx`: Overlay on proposal tracker during VOTING phase. Agent vote cells flip one by one (CSS transform rotateY). Staggered reveal (setTimeout). PASSED/FAILED/DEADLOCKED result. Summary toast.

- [ ] **Step 12: Create Debate page — Human Review Panel**

- `HumanReviewPanel.tsx`: Appears after scribing if HITL enabled. Shows findings/proposals awaiting review. Input box per item. Submit button → WebSocket message. Approve All / Override buttons with confirmation dialog.

- [ ] **Step 13: Create Debate page — Top Bar and Cost Meter**

- `PhaseIndicator.tsx`: Dot row for phases, active dot pulses
- `CostMeter.tsx`: Live cost with $ prefix, green color, monospace font, updates on every cost event

- [ ] **Step 14: Assemble Debate page**

`frontend/src/app/debate/[runId]/page.tsx`: Grid layout (left agent panels, center feed, right graph, bottom tracker). Connect to WebSocket on mount. Render all sub-components. Handle all UI states (loading, error, disconnected, long-running, budget exceeded).

- [ ] **Step 15: Create RFC Viewer page**

Match mockup `03-rfc-viewer.html`:
- `RFCDocument.tsx`: Clean document layout. Sticky sidebar with section links. All sections rendered: header, executive summary (pull-quote), critical findings (severity cards), proposals with inline vote matrix + dissent blocks, deadlocked items (side-by-side), action items (numbered), debate appendix (collapsible), cost summary table.
- `VoteMatrix.tsx`: 3 dots per proposal, colored by vote
- `DissentBlock.tsx`: Amber background, agent name, rationale

Export buttons: Markdown, JSON, HTML (download), PDF (window.print). Share link. Re-analyse button.

- [ ] **Step 16: Create Config page**

Match mockup `04-config.html`:
- 5 tabs: General, Providers, Agents, Ingestion, Output
- `GeneralTab.tsx`: Council name, max rounds, topology selector, HITL toggle, budget input
- `ProvidersTab.tsx`: Per-provider card with API key input (masked), model selector, test connection button with status indicator
- `AgentsTab.tsx`: Expandable agent cards with provider/model override, temperature slider, max tokens, persona editor, focus area chip toggles, vote weight slider, enable toggle
- `IngestionTab.tsx`: Source config, file limits, feature toggles
- `OutputTab.tsx`: Format checkboxes, directory, webhook URL
- Live validation on all fields. Save button. "Apply only to next run" checkbox.

- [ ] **Step 17: Create Sessions page**

Match mockup `05-sessions.html`:
- Filterable/sortable table with search, status filter, topology filter, sort dropdown
- Compare mode: checkbox per row, "Compare Selected" button → side-by-side RFC diff view
- Agent memory section: 4 cards showing per-agent learned patterns, clear memory button

- [ ] **Step 18: Create layout.tsx**

Root layout with: HTML head (title, meta), dark theme class, TopBar, main content area, Toaster for notifications.

- [ ] **Step 19: Implement themes**

Dark (default), Light, System (OS preference), High Contrast. Tailwind `dark:` classes + CSS custom properties. Theme toggle in TopBar. Persist to localStorage.

- [ ] **Step 20: Implement accessibility**

- Keyboard navigation (shadcn handles most)
- `aria-live="polite"` on agent status labels
- `prefers-reduced-motion` media query → disable animations
- Font size S/M/L toggle (CSS custom property `--font-scale`)
- Verify agent colors pass WCAG AA

- [ ] **Step 21: Commit**

```bash
git add frontend/
git commit -m "feat: React UI — all pages (home, debate, RFC, config, sessions), WebSocket, Zustand, React Flow"
```

---

## Task 16: Database Finalization

**Files:**
- Modify: `backend/src/codecouncil/db/models.py` — add indexes
- Modify: `backend/src/codecouncil/db/engine.py` — tune pooling

- [ ] **Step 1: Add database indexes**

```python
# On EventModel
Index("ix_events_run_sequence", "run_id", "sequence")
Index("ix_events_run_type", "run_id", "event_type")
Index("ix_events_run_agent", "run_id", "agent")

# On FindingModel
Index("ix_findings_run", "run_id")
Index("ix_findings_severity", "severity")

# On ProposalModel
Index("ix_proposals_run", "run_id")

# On VoteModel
Index("ix_votes_run", "run_id")
Index("ix_votes_proposal", "proposal_id")

# On RunModel
Index("ix_runs_status", "status")
Index("ix_runs_repo", "repo_url")

# On AgentMemoryModel
Index("ix_memories_agent", "agent_handle")
```

- [ ] **Step 2: Generate migration for indexes**

Run: `cd backend && alembic revision --autogenerate -m "add indexes"`

- [ ] **Step 3: Apply migration**

Run: `cd backend && alembic upgrade head`

- [ ] **Step 4: Commit**

```bash
git add backend/src/codecouncil/db/ backend/src/codecouncil/db/migrations/
git commit -m "feat: database finalization — indexes, connection pooling tuning"
```

---

## Task 17: Tests

**Files:**
- Modify: All test files
- Create any missing test files

- [ ] **Step 1: Ensure unit tests cover all core modules**

Verify tests exist and pass for:
- Config (schema validation, layer merge, env override)
- Models (all model creation, validation, enums)
- Providers (registry, fallback chain, cost tracking)
- Agents (registration, analyze/speak/vote with mocks, structured parsing)
- Topologies (turn order, interrupts, round ending)
- Ingestion (local source, each analyzer with mock data)
- Output (markdown render, JSON render, action item extraction, cost report)

- [ ] **Step 2: Ensure integration tests cover end-to-end**

- `test_graph_run.py`: Full graph run with mock providers → verify all phases → verify RFC output
- `test_api.py`: API endpoint tests with test DB → create run, get run, list runs, events, config, health

- [ ] **Step 3: Run all tests**

Run: `cd backend && pytest -v --cov=codecouncil`
Expected: all PASS, coverage report generated

- [ ] **Step 4: Commit**

```bash
git add backend/tests/
git commit -m "feat: complete test suite — unit tests for all modules, integration tests for graph and API"
```

---

## Task 18: README.md

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# CodeCouncil

> The world's first AI agent council for codebase intelligence.

Four AI agents with permanent identities analyse your codebase, debate in real time, and produce institutional-grade RFCs.

## Quickstart

```bash
git clone https://github.com/your-org/codecouncil.git
cd codecouncil
cp .env.example .env  # Add your API keys
make docker-up        # Start everything
open http://localhost:3000
```

## Agents

| Agent | Role | Personality |
|-------|------|-------------|
| The Archaeologist | Historian & evidence collector | Data-first, cites commits |
| The Skeptic | Risk analyst & challenger | Direct, names agents, can deadlock |
| The Visionary | Proposal author & domain reader | Constructive, defends with reasoning |
| The Scribe | Secretary & RFC author | Neutral witness, preserves dissent |

## Debate Topologies

- **Adversarial** (default) — Skeptic challenges every Visionary proposal
- **Collaborative** — Agents must reach consensus, no vote without alternative
- **Socratic** — Moderator questions each agent in turn
- **Open Floor** — Any agent responds to any other
- **Panel** — Fixed rotation per proposal
- **Custom** — Define your own in YAML

## Adding Custom Agents

1. Create a Python file implementing `BaseAgent`
2. Add config under `agents.custom` in your config YAML
3. Done — agent appears in UI and joins debate automatically

## Configuration

See `docs/configuration.md` for the full config reference.

## CLI

```bash
codecouncil analyse https://github.com/org/repo --stream
codecouncil serve
codecouncil sessions list
codecouncil agents memory show skeptic
codecouncil config show
```

## LLM Providers

OpenAI (default), Anthropic, Google Gemini, Mistral, Ollama (local), AWS Bedrock, Azure OpenAI.

Mix providers per agent — run Skeptic on GPT-4o and Visionary on Claude.

## License

MIT
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "feat: README with quickstart, agent roster, topology guide, custom agent docs"
```

---

## Final Verification

- [ ] **Run `make docker-up` and verify all services start**
- [ ] **Run `make test` and verify all tests pass**
- [ ] **Run `make demo` against a public repo and verify end-to-end**
- [ ] **Open http://localhost:3000 and verify UI loads**
- [ ] **Submit a repo and verify debate runs to completion**
- [ ] **Verify RFC is generated and viewable**
