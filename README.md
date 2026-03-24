<p align="center">
  <img src="docs/screenshots/home-dashboard.png" alt="CodeCouncil Dashboard" width="100%" />
</p>

<h1 align="center">CodeCouncil</h1>

<p align="center">
  <strong>AI agent council for codebase intelligence</strong><br/>
  Four permanent AI agents analyse your repository, debate in real time, and produce institutional-grade RFCs.
</p>

<p align="center">
  <a href="#features">Features</a> &middot;
  <a href="#screenshots">Screenshots</a> &middot;
  <a href="#quickstart">Quickstart</a> &middot;
  <a href="#architecture">Architecture</a> &middot;
  <a href="#agents">Agents</a> &middot;
  <a href="#configuration">Configuration</a> &middot;
  <a href="#development">Development</a> &middot;
  <a href="#license">License</a>
</p>

---

## Features

- **Multi-Agent Debate** — Four specialised AI agents with distinct roles analyse your codebase from different perspectives
- **Real-Time Streaming** — Watch agents think, challenge, and vote live via WebSocket
- **Institutional-Grade RFCs** — Produces structured reports with findings, proposals, vote matrices, and dissent records
- **7 LLM Providers** — OpenAI, Anthropic, Google Gemini, Mistral, Ollama (local), AWS Bedrock, Azure OpenAI
- **Mix Models Per Agent** — Run Skeptic on GPT-4o and Visionary on Claude Sonnet
- **6 Debate Topologies** — Adversarial, Collaborative, Socratic, Open Floor, Panel, Custom
- **Cost Tracking** — Per-agent, per-phase token usage and cost breakdown
- **Compare Repos** — Analyse two repositories side-by-side
- **Export Anywhere** — Markdown, JSON, HTML, Print/PDF
- **Dark & Light Mode** — Full theme support

---

## Screenshots

### Home Dashboard
Submit a repository URL, configure the analysis (provider, topology, rounds, budget), and monitor recent runs with cost and consensus metrics.

<p align="center">
  <img src="docs/screenshots/home-dashboard.png" alt="Home Dashboard" width="100%" />
</p>

### Live Debate View
Watch agents analyse in real time. The left panel shows each agent's status, findings, and voting positions. The centre shows the streaming debate feed with cost summary. The right panel tracks pipeline phases. Bottom shows proposal cards with pass/reject status.

<p align="center">
  <img src="docs/screenshots/debate-view.png" alt="Live Debate View" width="100%" />
</p>

### RFC Report
The final output: a structured Codebase Intelligence Report with consensus ring, agent roster with model badges, phase pipeline, stats cards, executive summary, critical findings, proposals with vote matrices, and full debate appendix.

<p align="center">
  <img src="docs/screenshots/rfc-report.png" alt="RFC Report" width="100%" />
</p>

---

## Quickstart

### Prerequisites

- Python 3.12+
- Node.js 18+
- PostgreSQL 16
- Redis 7
- Docker & Docker Compose (recommended)

### Quick Start with Docker

```bash
git clone https://github.com/riteshtk/code-council.git
cd code-council
cp backend/.env.example backend/.env   # Add your API keys
make docker-up                          # Start everything
open http://localhost:3000
```

### Manual Setup

```bash
# Clone
git clone https://github.com/riteshtk/code-council.git
cd code-council

# Backend
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd ..

# Frontend
cd frontend
npm install
cd ..

# Configure
cp backend/.env.example backend/.env
# Edit backend/.env and add your API keys (at minimum OPENAI_API_KEY)

# Start services (PostgreSQL + Redis)
docker compose up -d postgres redis

# Run migrations
make db-migrate

# Start both servers
make dev
```

Open [http://localhost:3000](http://localhost:3000) to access the UI.

---

## Architecture

```
codecouncil/
├── backend/              Python 3.12+ (FastAPI + LangGraph + SQLAlchemy async)
│   ├── src/codecouncil/
│   │   ├── api/          REST API + WebSocket endpoints
│   │   ├── agents/       Agent implementations (BaseAgent subclasses)
│   │   ├── providers/    LLM provider plugins (OpenAI, Anthropic, etc.)
│   │   ├── orchestrator/ LangGraph state machine (8 phases)
│   │   ├── models/       SQLAlchemy models
│   │   └── config/       7-layer config merge system
│   └── tests/
├── frontend/             Next.js 15 + TypeScript + Tailwind CSS + shadcn/ui
│   └── src/
│       ├── app/          Pages (home, debate/[runId], rfc/[runId], sessions, config)
│       ├── components/   UI components (debate/, rfc/, shared/)
│       └── lib/          API client, types, utilities, constants
└── docker-compose.yml    PostgreSQL + Redis + Backend + Frontend
```

### Pipeline Phases

```
INGEST → ANALYSE → OPENING → DEBATE ×N → VOTING → SCRIBING → REVIEW → FINALISE
```

| Phase | Description |
|-------|-------------|
| **Ingest** | Clone repo, parse files, build code graph |
| **Analyse** | Each agent independently reviews the codebase |
| **Opening** | Agents present initial positions and findings |
| **Debate** | N rounds of structured argumentation |
| **Voting** | Agents vote on each proposal (YES/NO/ABSTAIN/AMEND) |
| **Scribing** | Scribe synthesises debate into RFC draft |
| **Review** | Agents review and flag issues in the draft |
| **Finalise** | Final RFC generated with full audit trail |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, LangGraph, SQLAlchemy async, asyncpg |
| **Frontend** | Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, Zustand |
| **Database** | PostgreSQL 16 (via asyncpg + Alembic migrations) |
| **Cache** | Redis 7 (pub/sub + session cache) |
| **Events** | EventBus → PostgreSQL, WebSocket, SSE, Redis pub/sub, webhooks |
| **Orchestration** | Docker Compose |

---

## Agents

Four permanent agents with distinct roles, personalities, and voting behaviours:

| Agent | Handle | Role | Personality |
|-------|--------|------|-------------|
| **The Archaeologist** | `archaeologist` | Historian & Evidence Collector | Data-first, cites commits and metrics, votes on precedent |
| **The Skeptic** | `skeptic` | Risk Analyst & Challenger | Direct, names agents, challenges weak proposals, can declare deadlock |
| **The Visionary** | `visionary` | Proposal Author & Domain Reader | Constructive, drafts proposals, defends with reasoning |
| **The Scribe** | `scribe` | Secretary & RFC Author | Neutral witness, preserves dissent, synthesises final report |

Agents have **permanent memory** that persists across sessions, enabling them to build institutional knowledge about your codebase over time.

---

## Configuration

### LLM Providers

| Provider | Config Key | Models |
|----------|-----------|--------|
| OpenAI | `openai` | GPT-4o, GPT-4o-mini, GPT-5.4 |
| Anthropic | `anthropic` | Claude Sonnet, Claude Opus |
| Google | `gemini` | Gemini Pro, Gemini Ultra |
| Mistral | `mistral` | Mistral Large, Mixtral |
| Ollama | `ollama` | Any local model |
| AWS Bedrock | `bedrock` | Claude, Titan, Llama |
| Azure OpenAI | `azure` | GPT-4o, GPT-4 |

Mix providers per agent in `backend/.env` or via the Config page in the UI.

### Debate Topologies

| Topology | Description |
|----------|-------------|
| **Adversarial** (default) | Skeptic challenges every Visionary proposal |
| **Collaborative** | Agents must reach consensus; no vote without alternative |
| **Socratic** | Engine questions each agent in turn |
| **Open Floor** | Any agent responds to any other |
| **Panel** | Fixed rotation per proposal |
| **Custom** | Define your own in YAML |

### Environment Variables

```bash
# Required (at least one provider)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Database
DATABASE_URL=postgresql+asyncpg://codecouncil:codecouncil@localhost:5432/codecouncil

# Redis
REDIS_URL=redis://localhost:6379/0

# Optional providers
GOOGLE_API_KEY=
MISTRAL_API_KEY=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=

# Optional: repo access
GITHUB_TOKEN=
```

---

## Development

### Commands

```bash
make install        # Install all dependencies (backend + frontend)
make dev            # Start backend + frontend + PostgreSQL + Redis
make backend        # Start backend only (uvicorn on port 8000)
make frontend       # Start frontend only (Next.js on port 3000)
make db-migrate     # Run Alembic migrations
make db-reset       # Drop and recreate database
make test           # Run all tests
make test-backend   # Run backend tests only
make test-frontend  # Run frontend tests only
make lint           # Lint backend (ruff) + frontend (eslint)
make format         # Format backend (ruff) + frontend (prettier)
```

### CLI

```bash
codecouncil analyse https://github.com/org/repo --stream
codecouncil serve
codecouncil sessions list
codecouncil agents list
codecouncil config show
```

### Adding Custom Agents

1. Create a Python file implementing `BaseAgent`
2. Add config under `agents.custom` in your config YAML
3. The agent appears in the UI and joins debates automatically

### Extension Points

All use a registry pattern — implement the interface, register in config, and it's auto-discovered:

| Extension | Interface |
|-----------|-----------|
| Agents | `BaseAgent` |
| LLM Providers | `ProviderPlugin` |
| Topologies | `DebateTopology` |
| Ingestion Sources | `IngestionSource` |
| RFC Renderers | `RFCRenderer` |

---

## License

[MIT](LICENSE) - Ritesh Kumar
