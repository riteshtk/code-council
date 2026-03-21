# CodeCouncil — Design Specification

## Overview

CodeCouncil is an AI agent council for codebase intelligence. Four AI agents with permanent identities live in a shared council chamber, analyse repositories, debate in real time, challenge each other, vote on proposals, and produce institutional-grade RFCs. The council is extensible, multi-LLM, and always observable.

## Technology Decisions

| Decision | Choice |
|----------|--------|
| Orchestration | LangGraph |
| Database | PostgreSQL everywhere (SQLAlchemy async + Alembic + asyncpg) |
| Frontend | Next.js + TypeScript + Tailwind CSS + shadcn/ui |
| Graph visualization | React Flow |
| LLM providers | Official SDKs (openai, anthropic, google-generativeai, mistralai, boto3) |
| AST parsing | Tree-sitter (8 languages) |
| Python packaging | uv |
| Frontend packaging | npm |
| CVE + secrets | Custom built-in (OSV.dev API + regex patterns) |
| Deployment | Docker Compose (backend + frontend + PostgreSQL + Redis) |

## 1. Project Structure

```
codecouncil/
├── backend/
│   ├── src/
│   │   └── codecouncil/
│   │       ├── __init__.py
│   │       ├── main.py                    # FastAPI app entry
│   │       ├── cli.py                     # Typer CLI entry
│   │       ├── config/
│   │       │   ├── __init__.py
│   │       │   ├── schema.py              # Pydantic config models
│   │       │   ├── loader.py              # 7-layer config merge
│   │       │   └── defaults.py            # Built-in defaults + persona prompts
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── state.py               # CouncilState, RunState
│   │       │   ├── events.py              # Event, EventType enums
│   │       │   ├── findings.py            # Finding, Severity
│   │       │   ├── proposals.py           # Proposal, ProposalStatus
│   │       │   ├── votes.py               # Vote, VoteType
│   │       │   ├── agents.py              # AgentIdentity, AgentMemory
│   │       │   ├── repo.py                # RepoContext, FileInfo, GitLog
│   │       │   └── rfc.py                 # RFC, RFCSection
│   │       ├── events/
│   │       │   ├── __init__.py
│   │       │   ├── bus.py                 # EventBus (asyncio + Redis pub/sub)
│   │       │   ├── persistence.py         # Event → PostgreSQL
│   │       │   ├── websocket.py           # WebSocket publisher
│   │       │   └── sse.py                 # SSE publisher
│   │       ├── providers/
│   │       │   ├── __init__.py
│   │       │   ├── base.py                # ProviderPlugin interface
│   │       │   ├── registry.py            # Provider registry
│   │       │   ├── cost.py                # Cost tracking + pricing tables
│   │       │   ├── openai_provider.py
│   │       │   ├── anthropic_provider.py
│   │       │   ├── google_provider.py
│   │       │   ├── mistral_provider.py
│   │       │   ├── ollama_provider.py
│   │       │   ├── bedrock_provider.py
│   │       │   └── azure_provider.py
│   │       ├── ingestion/
│   │       │   ├── __init__.py
│   │       │   ├── base.py                # IngestionSource interface
│   │       │   ├── registry.py            # Source registry
│   │       │   ├── github.py              # GitHub API + clone
│   │       │   ├── gitlab.py
│   │       │   ├── bitbucket.py
│   │       │   ├── local.py               # Local directory
│   │       │   ├── archive.py             # .zip / .tar.gz
│   │       │   ├── analyzers/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── churn.py           # Churn rate calculator
│   │       │   │   ├── bus_factor.py
│   │       │   │   ├── dead_code.py
│   │       │   │   ├── ast_parser.py      # Tree-sitter multi-language
│   │       │   │   ├── dependency.py      # Package file parsing
│   │       │   │   ├── cve.py             # OSV.dev API scanner
│   │       │   │   ├── secrets.py         # Regex-based secret detection
│   │       │   │   ├── licence.py         # Licence detection
│   │       │   │   ├── git_history.py     # Commit parsing + sentiment
│   │       │   │   └── incremental.py     # Content hash diffing
│   │       │   └── context.py             # Builds RepoContext from analyzers
│   │       ├── agents/
│   │       │   ├── __init__.py
│   │       │   ├── base.py                # BaseAgent
│   │       │   ├── registry.py            # Agent registry
│   │       │   ├── memory.py              # Agent memory load/save/summarize
│   │       │   ├── archaeologist.py
│   │       │   ├── skeptic.py
│   │       │   ├── visionary.py
│   │       │   └── scribe.py
│   │       ├── debate/
│   │       │   ├── __init__.py
│   │       │   ├── base.py                # DebateTopology interface
│   │       │   ├── registry.py            # Topology registry
│   │       │   ├── adversarial.py
│   │       │   ├── collaborative.py
│   │       │   ├── socratic.py
│   │       │   ├── open_floor.py
│   │       │   ├── panel.py
│   │       │   └── custom.py              # YAML-defined topology
│   │       ├── graph/
│   │       │   ├── __init__.py
│   │       │   ├── council_graph.py       # LangGraph state graph definition
│   │       │   ├── nodes.py               # All graph nodes
│   │       │   └── checkpointing.py       # PostgreSQL-backed checkpointer
│   │       ├── output/
│   │       │   ├── __init__.py
│   │       │   ├── base.py                # RFCRenderer interface
│   │       │   ├── registry.py            # Renderer registry
│   │       │   ├── markdown.py
│   │       │   ├── json_renderer.py
│   │       │   ├── html.py                # Jinja2 template
│   │       │   ├── templates/
│   │       │   │   └── rfc.html.j2
│   │       │   ├── action_items.py        # Action item extractor
│   │       │   └── cost_report.py         # Cost report generator
│   │       ├── api/
│   │       │   ├── __init__.py
│   │       │   ├── app.py                 # FastAPI app factory
│   │       │   ├── middleware.py           # CORS, logging, errors, rate limiting
│   │       │   ├── routes/
│   │       │   │   ├── __init__.py
│   │       │   │   ├── runs.py
│   │       │   │   ├── config.py
│   │       │   │   ├── personas.py
│   │       │   │   ├── agents.py
│   │       │   │   ├── providers.py
│   │       │   │   ├── sessions.py
│   │       │   │   └── health.py
│   │       │   ├── websocket.py           # WS /ws/runs/{id}/debate
│   │       │   ├── sse.py                 # SSE /api/runs/{id}/stream
│   │       │   └── metrics.py             # Prometheus /metrics
│   │       └── db/
│   │           ├── __init__.py
│   │           ├── engine.py              # SQLAlchemy async engine setup
│   │           ├── models.py              # ORM table models
│   │           ├── repositories.py        # Data access layer
│   │           └── migrations/
│   │               └── alembic/
│   │                   ├── env.py
│   │                   └── versions/
│   ├── tests/
│   │   ├── unit/
│   │   │   ├── test_config.py
│   │   │   ├── test_agents.py
│   │   │   ├── test_parsers.py
│   │   │   ├── test_topology.py
│   │   │   ├── test_providers.py
│   │   │   ├── test_ingestion.py
│   │   │   └── test_output.py
│   │   └── integration/
│   │       ├── test_graph_run.py
│   │       └── test_api.py
│   ├── pyproject.toml
│   ├── alembic.ini
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx                   # Home page
│   │   │   ├── debate/[runId]/
│   │   │   │   └── page.tsx               # Debate page
│   │   │   ├── rfc/[runId]/
│   │   │   │   └── page.tsx               # RFC viewer
│   │   │   ├── config/
│   │   │   │   └── page.tsx               # Config page
│   │   │   └── sessions/
│   │   │       └── page.tsx               # Sessions page
│   │   ├── components/
│   │   │   ├── ui/                        # shadcn/ui components
│   │   │   ├── debate/
│   │   │   │   ├── AgentPanel.tsx
│   │   │   │   ├── DebateFeed.tsx
│   │   │   │   ├── GraphVisualizer.tsx    # React Flow
│   │   │   │   ├── ProposalTracker.tsx
│   │   │   │   ├── VoteReveal.tsx
│   │   │   │   ├── HumanReviewPanel.tsx
│   │   │   │   ├── CostMeter.tsx
│   │   │   │   └── PhaseIndicator.tsx
│   │   │   ├── rfc/
│   │   │   │   ├── RFCDocument.tsx
│   │   │   │   ├── VoteMatrix.tsx
│   │   │   │   └── DissentBlock.tsx
│   │   │   ├── config/
│   │   │   │   ├── GeneralTab.tsx
│   │   │   │   ├── ProvidersTab.tsx
│   │   │   │   ├── AgentsTab.tsx
│   │   │   │   ├── IngestionTab.tsx
│   │   │   │   └── OutputTab.tsx
│   │   │   ├── home/
│   │   │   │   ├── RepoInput.tsx
│   │   │   │   ├── QuickConfig.tsx
│   │   │   │   ├── RecentRuns.tsx
│   │   │   │   └── CouncilHealth.tsx
│   │   │   └── shared/
│   │   │       ├── TopBar.tsx
│   │   │       ├── Skeleton.tsx
│   │   │       └── ErrorBoundary.tsx
│   │   ├── stores/
│   │   │   ├── runStore.ts                # Zustand store
│   │   │   ├── configStore.ts
│   │   │   └── websocketManager.ts        # WS connection + reconnect
│   │   ├── lib/
│   │   │   ├── api.ts                     # REST API client
│   │   │   ├── types.ts                   # TypeScript types
│   │   │   └── utils.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   └── .env.example
├── docs/
│   ├── architecture.md
│   ├── agents.md
│   ├── topologies.md
│   ├── configuration.md
│   ├── custom-agents.md
│   ├── api-reference.md
│   └── superpowers/
│       └── specs/
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── Makefile
├── .env.example
├── .gitignore
├── CLAUDE.md
└── README.md
```

## 2. Tech Stack

### Backend (Python 3.12+)

- **Framework:** FastAPI + Uvicorn
- **Orchestration:** LangGraph
- **Database:** SQLAlchemy async + asyncpg + Alembic
- **LLM SDKs:** openai, anthropic, google-generativeai, mistralai, boto3
- **AST Parsing:** tree-sitter + language grammars
- **Event Bus:** asyncio queues + optional Redis (redis-py)
- **CLI:** Typer + Rich
- **WebSocket:** FastAPI native
- **SSE:** sse-starlette
- **Metrics:** prometheus-client
- **Templates:** Jinja2
- **HTTP Client:** httpx (async)
- **Config:** PyYAML + Pydantic v2
- **Testing:** pytest + pytest-asyncio + respx

### Frontend (Node 20+)

- **Framework:** Next.js 15 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS v4
- **Components:** shadcn/ui
- **State:** Zustand
- **Graph:** React Flow
- **Icons:** Lucide React
- **Testing:** Vitest

### Infrastructure

- Docker Compose: backend, frontend, PostgreSQL 16, Redis 7
- Makefile for all dev commands

## 3. Data Flow

### End-to-end flow for a council run

```
User submits repo URL
        │
        ▼
   ┌─────────┐     POST /api/runs
   │  API     │◄──────────────────── Frontend / CLI
   │  Server  │
   └────┬─────┘
        │ Creates Run record in DB, emits run_started event
        ▼
   ┌─────────┐
   │ LangGraph│    State: CouncilState (passed between all nodes)
   │  Graph   │
   └────┬─────┘
        │
        ├──► Node: INGEST
        │    Clone/fetch repo, run all analyzers in parallel
        │    (churn, bus_factor, dead_code, AST, deps, CVE, secrets)
        │    Output: RepoContext added to state
        │
        ├──► Node: ANALYSE
        │    Fan-out: Archaeologist, Skeptic, Visionary run in parallel
        │    Each agent gets RepoContext + persona prompt
        │    Each emits findings via EventBus
        │    Output: findings[] added to state
        │
        ├──► Node: OPENING
        │    Sequential: each agent presents findings (no cross-talk)
        │    Order: Archaeologist → Skeptic → Visionary
        │    Output: opening_statements[] added to state
        │
        ├──► Node: DEBATE
        │    Topology engine controls turn order
        │    Proposals created, challenged, revised
        │    Each turn: agent LLM call → parse structured output → emit events
        │    Loop until max_rounds or all proposals resolved
        │    Deadlock can short-circuit any proposal
        │    Conditional edge: if rounds < max AND unresolved proposals → loop
        │
        ├──► Node: VOTING
        │    Each voting agent votes on each proposal
        │    Scribe does not vote on proposals
        │    Output: votes[] added to state, proposal statuses updated
        │
        ├──► Node: SCRIBING
        │    Scribe synthesizes full RFC from state
        │    Output: rfc_content added to state
        │
        ├──► Node: REVIEW (conditional: only if hitl_enabled)
        │    Pauses graph, waits for human input
        │    Human can challenge, override, approve, or request re-debate
        │    Timeout: auto-approve after hitl_timeout_minutes
        │
        └──► Node: FINALISE
             Save RFC to file + DB
             Update agent memories
             Emit rfc_finalised + run_completed events
             Calculate consensus score
```

### Event flow (real-time)

```
Agent LLM call → EventBus.emit(event) → simultaneously:
    ├──► PostgreSQL (persistence)
    ├──► WebSocket publisher → connected browsers
    ├──► SSE publisher → SSE clients
    ├──► Redis pub/sub (if multi-process)
    └──► Webhook POST (if configured)
```

### State management

- Backend: CouncilState is a Pydantic model passed through LangGraph. Accumulates: repo_context, findings, proposals, votes, debate_rounds, rfc_content.
- Frontend: Zustand store receives events via WebSocket, reconstructs run state incrementally. No polling — pure event-driven.

## 4. Agent System

### BaseAgent interface

```python
class BaseAgent:
    identity: AgentIdentity          # name, handle, color, role
    config: AgentConfig              # provider, model, temperature, etc.
    memory: AgentMemory              # loaded at session start

    async def analyze(state: CouncilState) -> list[Finding]
    async def speak(state: CouncilState, context: DebateContext) -> AgentResponse
    async def vote(proposal: Proposal, state: CouncilState) -> Vote
    async def update_memory(state: CouncilState) -> None
```

Every agent method:
1. Constructs a prompt from persona + relevant state
2. Calls its configured LLM provider (with streaming)
3. Parses structured output (findings, proposals, votes)
4. Emits events to EventBus during streaming
5. Returns typed result

### Structured output parsing

Agents return free-form text parsed into structured objects:
- System prompt instructs agents to use markers: `[FINDING:CRITICAL]`, `[PROPOSAL]`, `[VOTE:YES]`, etc.
- A parser extracts these from the stream in real-time as tokens arrive
- Chips appear in the UI as findings/proposals are parsed mid-stream

### Cross-agent addressing

During debate, each agent receives the full debate history. The topology engine injects:
- Who spoke last
- Which agent is being addressed
- Which proposal is under discussion
- The addressed agent gets priority in next turn

### Default agents

**The Archaeologist** — Historian and evidence collector. Declarative, grim, data-first. Speaks first. Focuses on: churn rate, bus factor, dead code, TODO accumulation, commit sentiment, file age, author concentration, rewrite frequency. Votes based on historical precedent.

**The Skeptic** — Risk analyst and challenger. Clipped, direct, precise. Can declare DEADLOCK with evidence. Focuses on: security surface, coupling, CVE exposure, test coverage gaps, API contracts, performance, hidden dependencies, blast radius. Votes no with explicit rationale, concedes only when fully convinced.

**The Visionary** — Proposal author and domain model reader. Constructive but not naive. Focuses on: DDD patterns, refactor paths, design pattern upgrades, bounded contexts, module boundaries, architecture evolution. Votes yes on own proposals unless convinced otherwise, can withdraw proposals.

**The Scribe** — Council secretary and RFC author. Neutral witness. Preserves voices, does not smooth over disagreement. Focuses on synthesis only. Does not vote on proposals, votes only on RFC completeness.

### Agent memory lifecycle

```
Session start → Load compressed summaries from DB
Analysis      → Agent references past patterns
Debate        → Agent references interpersonal history
Session end   → Summarize this session → Save to DB
```

Memory is always summarized (not raw transcripts). Each entry has a token count; old entries pruned when total exceeds configurable limit.

### Extensibility

Adding a new agent requires exactly 2 things:

1. Create a Python file implementing BaseAgent with identity, persona, focus areas
2. Add config entry under `agents.custom[]`

No other code changes. The agent auto-registers, appears in UI, joins debate per its role.

Same pattern for all extension points:

| Extension | Implement | Register in config | Auto-discovered |
|-----------|-----------|-------------------|-----------------|
| Agent | BaseAgent | agents.custom[] | Yes |
| Provider | ProviderPlugin | llm.providers | Yes |
| Topology | DebateTopology | topology registry | Yes |
| Ingestion source | IngestionSource | ingestion registry | Yes |
| RFC renderer | RFCRenderer | renderer registry | Yes |

Plugin discovery: scan `~/.codecouncil/plugins/` on startup, auto-import .py files, register any matching classes. Hot-reload in dev mode.

## 5. Debate Topology Engine

### DebateTopology interface

```python
class DebateTopology:
    def get_turn_order(state: CouncilState) -> list[AgentTurn]
    def can_interrupt(agent: str, current_speaker: str) -> bool
    def should_end_round(state: CouncilState, round: int) -> bool
    def get_next_speaker(state: CouncilState, last_turn: AgentTurn) -> str | None
    def on_deadlock(proposal: Proposal, agent: str, evidence: str) -> None
```

### Topology behaviors

| Topology | Turn Logic | Interrupts | Round Ends When |
|----------|-----------|------------|-----------------|
| Adversarial (default) | Visionary presents → Skeptic challenges → Visionary responds → Others → Skeptic final word | Skeptic can deadlock | All proposals addressed or max rounds |
| Collaborative | Arch → Visionary → Skeptic (must include mitigations) → consensus check | None | Modified consensus or max rounds |
| Socratic | Topology engine acts as Moderator (no separate agent needed) — questions each agent in turn. Agents speak only when addressed. | Only Moderator (engine) | All agents questioned on all proposals |
| Open Floor | Any agent responds to any other. Max 1 response per agent per turn. | All agents | Timer or max responses |
| Panel | Fixed rotation per proposal. No interruptions. | None | All agents spoken |
| Custom | User-defined YAML steps with conditions | Per step config | All steps executed |

### Custom topology YAML

```yaml
council:
  debate_topology: custom
  custom_topology:
    - agent: archaeologist
      action: present_findings
    - agent: visionary
      action: propose
    - agent: skeptic
      action: challenge
      target: visionary
    - agent: visionary
      action: respond
      target: skeptic
    - agent: skeptic
      action: challenge
      condition: "if skeptic.vote == no"
    - agent: all
      action: vote
```

### Proposal lifecycle

PROPOSED → CHALLENGED → REVISED (0-N times) → VOTED → PASSED | FAILED | DEADLOCKED

### Voting system

- Each voting agent casts: YES | NO | ABSTAIN with rationale and confidence (0.0-1.0)
- Threshold configurable: simple majority (default) | supermajority | unanimous
- CRITICAL findings require configurable threshold (default: unanimous)
- Scribe does not vote on proposals
- Abstain counts toward quorum but not pass/fail

## 6. Provider System

### ProviderPlugin interface

```python
class ProviderPlugin:
    name: str

    async def stream(messages: list[Message], config: LLMConfig) -> AsyncIterator[str]
    async def complete(messages: list[Message], config: LLMConfig) -> str
    def count_tokens(text: str) -> int
    def supports_streaming() -> bool
    def max_context_tokens() -> int
```

### Providers

| Provider | SDK | Streaming | Token Counting | Notes |
|----------|-----|-----------|---------------|-------|
| OpenAI | openai | Yes | tiktoken | Default |
| Anthropic | anthropic | Yes | API returns counts | Prompt caching support |
| Google | google-generativeai | Yes | API returns counts | Gemini |
| Mistral | mistralai | Yes | tiktoken estimate | |
| Ollama | openai (compatible) | Yes | tiktoken estimate | localhost:11434 |
| Bedrock | boto3 | Yes (EventStream) | tiktoken estimate | invoke_model_with_response_stream |
| Azure | openai (base_url) | Yes | tiktoken | Same SDK, different endpoint |

### Fallback chain

Try primary → on failure (timeout, rate limit, error) → log fallback event → try next in chain → repeat until success or chain exhausted → if all fail: agent_error event, run failed.

### Cost tracking

- Every LLM call records: provider, model, input_tokens, output_tokens, latency_ms
- Cost calculated from built-in pricing table
- Budget enforcement: if run_cost > budget_limit_usd → pause graph → emit budget_exceeded → wait for user continue/cancel

### Anthropic prompt caching

- Agent persona: `cache_control: {"type": "ephemeral"}` on system message
- RepoContext: `cache_control: {"type": "ephemeral"}` on user message
- Cache hits logged in events and cost tracking

## 7. Ingestion System

### Source adapters

| Source | Mechanism |
|--------|-----------|
| GitHub API | REST API for file tree + contents, clone for large repos or git history |
| GitLab | REST API + clone (token auth) |
| Bitbucket | REST API + clone (token/SSH auth) |
| Local | Direct filesystem scan, git log if .git present |
| Archive | Extract to temp dir, scan as local |

### Analyzers (all run in parallel, all async)

| Analyzer | Output |
|----------|--------|
| git_history | Commits, per-file authors, branch topology, commit sentiment |
| churn | Per-file churn rate (commits/total in window) |
| bus_factor | Per-module author count, flag if < threshold |
| dead_code | Functions/modules with zero inbound references |
| ast_parser | Tree-sitter → function/class inventory, import graph, circular deps, LOC, complexity |
| dependency | Parse manifests → package list with current vs latest version |
| cve | OSV.dev /v1/querybatch API → vulnerabilities per package |
| test_coverage | Detect test files, compute test-to-source ratio, parse coverage files (.coverage, lcov.info) if present |
| secrets | Regex patterns for AWS keys, API tokens, passwords. Results hashed. |
| licence | Detect licence type, flag incompatibilities |

### Incremental ingestion

First run: hash every file → store in DB → full analysis.
Next run: diff against stored hashes → re-analyze only changed files → merge with cached RepoContext.

### RepoContext output

```python
class RepoContext:
    repo_url: str
    repo_name: str
    file_tree: list[FileInfo]
    git_log: list[Commit]
    churn_report: ChurnReport
    bus_factor_report: BusFactorReport
    dead_code: list[DeadCodeItem]
    import_graph: ImportGraph
    circular_deps: list[CircularDep]
    dependencies: list[Dependency]
    cve_results: list[CVEResult]
    secret_findings: list[SecretFinding]
    licence_report: LicenceReport
    test_coverage: TestCoverage
    summary_stats: RepoStats
```

## 8. API, WebSocket & Events

### REST API

| Method | Endpoint | Behavior |
|--------|----------|----------|
| POST | /api/runs | Validate config, create Run, launch graph as background task, return run_id |
| GET | /api/runs | List all runs (paginated) |
| GET | /api/runs/{id} | Full run state |
| DELETE | /api/runs/{id} | Cancel in-progress run (graceful) |
| POST | /api/runs/{id}/review | Submit human challenge/override |
| GET | /api/runs/{id}/rfc | Get RFC (markdown/json/html via Accept header) |
| GET | /api/runs/{id}/events | Paginated events (filter by agent, type, phase) |
| GET | /api/runs/{id}/cost | Cost breakdown |
| POST | /api/runs/{id}/rerun | Re-run with same or new config |
| GET | /api/config | Current merged config (secrets masked) |
| POST | /api/config/validate | Validate config YAML |
| PATCH | /api/config | Update user config |
| GET | /api/personas | List personas |
| GET | /api/personas/{name} | Get persona |
| POST | /api/personas | Create custom persona |
| PUT | /api/personas/{name} | Update persona |
| DELETE | /api/personas/{name} | Delete persona |
| GET | /api/agents | List agents + status |
| GET | /api/agents/{handle}/memory | Get memory summary |
| DELETE | /api/agents/{handle}/memory | Clear memory |
| GET | /api/providers | List providers + status |
| POST | /api/providers/test | Test provider connectivity |
| GET | /api/sessions | List past sessions |
| GET | /api/sessions/{id} | Session detail |
| GET | /api/sessions/compare | Compare two sessions |
| GET | /api/health | System health + provider connectivity |
| GET | /metrics | Prometheus metrics |

### WebSocket

```
WS /ws/runs/{run_id}/debate
  ← Replay all historical events on connect
  ← Stream new events in real-time
  → Client sends: { type: "human_challenge", finding_id, content }
  ← Ping every 15s, client pongs within 10s
  ← run_completed event then close on completion
  Reconnect: last_sequence param → replay from that sequence
```

### SSE

```
GET /api/runs/{id}/stream
  Server-sent events, same events as WebSocket
  Supports Last-Event-ID for reconnect
```

### EventBus

```python
class EventBus:
    async def emit(event: Event) -> None:
        await asyncio.gather(
            self._persist_to_db(event),
            self._publish_to_websockets(event),
            self._publish_to_sse(event),
            self._publish_to_redis(event),
            self._post_to_webhook(event),
        )

    def subscribe(run_id: str) -> AsyncIterator[Event]
    def replay(run_id: str, after_sequence: int) -> AsyncIterator[Event]
```

Every event gets monotonically increasing sequence number per run.

### Prometheus metrics

- `codecouncil_runs_total{status}` — counter
- `codecouncil_runs_active` — gauge
- `codecouncil_llm_call_duration_seconds{provider,model}` — histogram
- `codecouncil_tokens_total{provider,model,direction}` — counter
- `codecouncil_cost_usd_total{provider,model}` — counter
- `codecouncil_websocket_connections` — gauge

### Middleware

Request → CORS → Rate Limiter (100 req/min per IP) → Request Logging → Route Handler → Error Handler → Response

## 9. Database

PostgreSQL everywhere. SQLAlchemy async + asyncpg + Alembic migrations.

### Tables

- **runs:** id, repo_url, repo_name, status, phase, config_snapshot, started_at, completed_at, total_cost_usd, consensus_score
- **events:** id, run_id, sequence, agent, event_type, phase, round, content, structured, provider, model, input_tokens, output_tokens, cost_usd, latency_ms, cached, created_at
- **findings:** id, run_id, agent, severity, scope, content, implication, created_at
- **proposals:** id, run_id, proposal_number, version, title, goal, effort, status, author_agent, created_at, updated_at
- **votes:** id, run_id, proposal_id, agent, vote, rationale, confidence, created_at
- **sessions:** id, name, runs (array of run_ids), created_at
- **agent_memories:** id, agent_handle, session_id, summary, token_count, created_at
- **personas:** id, name, content, is_default, created_at, updated_at

### Connection pooling

pool_size=10, max_overflow=20, connection recycling every 300s, health check on checkout.

### File storage

```
output/{run_id}/rfc.md
output/{run_id}/rfc.json
output/{run_id}/events.jsonl
output/{run_id}/debate_transcript.md
output/{run_id}/cost_report.json
```

## 10. CLI

All commands via Typer with Rich terminal UI:

```
codecouncil analyse <repo-url-or-path> [options]
codecouncil serve [--api-port N] [--ui-port N] [--no-ui]
codecouncil sessions list|show|compare
codecouncil agents list|memory show|memory clear
codecouncil personas list|add|edit|remove
codecouncil providers list|test
codecouncil config show|validate|set
```

### Terminal UI (Rich)

- Agent panels: Rich Columns (side-by-side when terminal wide enough)
- Streaming debate feed: Rich Live + Panel
- Vote matrix: Rich Table with colored cells
- Cost meter in header: updated in real time
- RFC output: syntax-highlighted Markdown
- All events optionally saved to .jsonl

## 11. UI Pages

### Home Page

- Repo URL input with source selector (GitHub/GitLab/Bitbucket/Local/Archive)
- Quick config: provider, topology, rounds, agent toggles, HITL, budget
- Recent runs grid: repo, date, consensus %, cost, status
- Council health: agent readiness + provider connectivity

### Debate Page (hero page)

- **Top bar:** Repo name, status pill, phase indicator dots, round counter, elapsed time, live cost meter, provider badges
- **Left — Agent panels (4 quadrants):** Avatar with pulse animation when speaking, status label, streaming text with cursor, finding/proposal chips, mini vote record
- **Center — Debate feed:** Chronological event stream with color-coded bubbles (findings, challenges, proposals, revisions, deadlocks, votes). Search/filter bar. Auto-scroll.
- **Right — Graph visualizer:** React Flow topology diagram. Active node glows. Completed nodes show checkmark. Clickable nodes.
- **Bottom — Proposal tracker:** Card per proposal with status, vote tally dots, animated state transitions. Deadlocked cards have red border.
- **Vote reveal:** Staggered card-flip animation. Summary toast after all votes.
- **Human review panel:** Appears after Scribe. Per-finding input boxes. Approve/Override buttons.

### RFC Viewer

- Clean document layout with sticky sidebar navigation
- Sections: header, executive summary (pull-quote), critical findings (severity-bordered), proposals with inline vote matrix, dissent blocks (amber), deadlocked items (side-by-side positions), action items (numbered, effort-badged), human review notes, debate appendix (collapsible), cost summary table
- Export: Markdown, JSON, HTML, PDF (browser print)
- Share link, Re-analyse button

### Config Page

- 5 tabs: General, Providers, Agents, Ingestion, Output
- General: council name, max rounds, topology selector, HITL, budget
- Providers: per-provider API key (masked), model selector, test connection button
- Agents: enable toggle, provider/model override, temperature slider, max tokens, persona editor, focus area chips, vote weight
- Ingestion: source config, file limits, feature toggles
- Output: formats, directory, webhook
- Live validation, Save button, "Apply only to next run" checkbox

### Sessions Page

- Filterable/sortable session table: repo, date, agents, topology, consensus, cost, status
- Comparison mode: select 2 runs, diff RFCs
- Agent memory viewer: per-agent learned patterns across sessions

## 12. UI States & Edge Cases

- **Loading:** Skeleton screens (shadcn Skeleton)
- **Empty:** Centered call to action
- **Error:** Last event + error detail
- **Disconnected:** Yellow banner with auto-reconnect (exponential backoff)
- **Long-running:** Toast if > 5 minutes
- **Provider fallback:** Yellow notice in agent panel
- **Budget exceeded:** Modal with cost + continue/cancel
- **Demo mode:** Replay pre-recorded run from JSON, configurable delay, no API keys needed

## 13. Themes & Accessibility

- **Themes:** Dark (default), Light, System (OS preference), High Contrast
- **Keyboard:** All interactive elements navigable (shadcn/ui)
- **Screen readers:** aria-live on agent status changes
- **Reduced motion:** prefers-reduced-motion disables animations, instant vote reveals
- **Font size:** S/M/L toggle via CSS custom property scaling
- **Agent colors:** WCAG AA on both dark and light themes
- **Sound:** Optional sound on vote and deadlock (Web Audio API, off by default)

## 14. Security

- API keys never logged or included in events
- GET /api/config masks all key/token fields
- Secret detection: original values SHA-256 hashed, only hash + location stored
- No code from ingested repos executed (tree-sitter AST parse only)
- Rate limiting: 100 req/min per IP
- CORS configured per deployment

## 15. Reliability & Performance

- **Retry:** Exponential backoff on LLM failures, fallback chain per agent
- **Checkpointing:** LangGraph PostgreSQL-backed checkpointer after each phase. Resume from last checkpoint on failure.
- **WebSocket reconnect:** Event replay from last sequence. No events lost.
- **Graceful shutdown:** On SIGTERM/SIGINT, checkpoint state, close WebSockets with reason, save in-progress runs
- **Analysis phase:** < 60s for 500 files (3 parallel agents)
- **Debate turn:** < 30s per agent
- **WebSocket lag:** < 100ms emission to render
- **RFC render:** < 2s
- **API p95:** < 200ms (non-streaming)

## 16. RFC Versioning

- RFC has version number, increments on re-analysis of same repo
- Rerun creates new run linked to same repo
- Scribe includes changelog section noting changes between versions

## 17. Webhook System

- `output.webhook_url` in config
- Every event: async POST with event JSON
- On completion: POST full RFC JSON
- 5s timeout, fire-and-forget (failure logged, doesn't block)

## 18. Configuration System

7-layer merge (lowest to highest priority):
1. Built-in defaults (hardcoded)
2. Global config (~/.codecouncil/config.yaml)
3. Project config (.codecouncil.yaml in repo root)
4. Runtime config (--config flag)
5. Environment variables (CC_AGENTS__SKEPTIC__TEMPERATURE=0.2)
6. API request body overrides
7. UI quick-settings

Full schema documented in original requirements spec Section 6.2.

## 19. Build Order

Strictly sequential, each step complete before next:

1. CLAUDE.md
2. Project scaffold (full directory tree, pyproject.toml, package.json, Makefile, .env.example)
3. Config system (schema, loader, defaults, 4 persona prompts)
4. Data models (all Pydantic models)
5. Database foundation (SQLAlchemy engine, ORM models, initial Alembic migration with all tables — needed by steps 6-12)
6. Event system (EventBus, persistence to DB, WebSocket/SSE publishers)
7. Provider system (interface, 7 implementations, fallback, cost tracking)
8. Ingestion system (source adapters, all analyzers, incremental diffing)
9. Agent system (BaseAgent, 4 agents, streaming, memory)
10. Debate topologies (5 built-in + custom, registry)
11. LangGraph graph (all nodes, edges, checkpointing, HITL)
12. Output system (RFC renderers, templates, action items, cost report)
13. API server (all routes, WebSocket, SSE, middleware, health, metrics)
14. CLI (all commands, Rich terminal UI)
15. React UI (all pages, components, Zustand, WebSocket manager)
16. Database finalization (indexes, connection pooling tuning, seed data)
17. Tests (unit + integration)
18. README.md
