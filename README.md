# CodeCouncil

> The world's first AI agent council for codebase intelligence.

Four AI agents with permanent identities analyse your codebase, debate in real time, and produce institutional-grade RFCs.

## Quickstart

```bash
git clone <repo-url>
cd codecouncil
cp .env.example .env  # Add your API keys
make docker-up        # Start everything
open http://localhost:3000
```

## Agents

| Agent | Role | Personality |
|-------|------|-------------|
| The Archaeologist | Historian & evidence collector | Data-first, cites commits, votes on precedent |
| The Skeptic | Risk analyst & challenger | Direct, names agents, can declare deadlock |
| The Visionary | Proposal author & domain reader | Constructive, defends with reasoning |
| The Scribe | Secretary & RFC author | Neutral witness, preserves dissent |

## Debate Topologies

- **Adversarial** (default) — Skeptic challenges every Visionary proposal
- **Collaborative** — Agents must reach consensus, no vote without alternative
- **Socratic** — Engine questions each agent in turn
- **Open Floor** — Any agent responds to any other
- **Panel** — Fixed rotation per proposal
- **Custom** — Define your own in YAML

## Adding Custom Agents

1. Create a Python file implementing `BaseAgent`
2. Add config under `agents.custom` in your config YAML
3. Done — agent appears in UI and joins debate automatically

## CLI

```bash
codecouncil analyse https://github.com/org/repo --stream
codecouncil serve
codecouncil sessions list
codecouncil agents list
codecouncil config show
```

## LLM Providers

OpenAI (default), Anthropic, Google Gemini, Mistral, Ollama (local), AWS Bedrock, Azure OpenAI.

Mix providers per agent — run Skeptic on GPT-4o and Visionary on Claude.

## Development

```bash
make install     # Install all dependencies
make dev         # Start dev servers
make test        # Run all tests
make lint        # Lint everything
make format      # Format everything
```

## Architecture

- **Backend:** Python 3.12+ / FastAPI / LangGraph / SQLAlchemy async
- **Frontend:** Next.js 15 / TypeScript / Tailwind CSS / shadcn/ui
- **Database:** PostgreSQL 16
- **Cache:** Redis 7
- **Orchestration:** Docker Compose

## License

MIT
