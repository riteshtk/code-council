# Agent Architecture Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hardcoded dual-system agent architecture with a single data-driven `AgentDefinition` model — one file per agent, auto-discovered, DB-backed, fully stateless.

**Architecture:** Each agent is an `AgentDefinition` Pydantic model containing identity, persona, prompts, config, and policies. The pipeline reads from definitions instead of hardcoding prompts. The framework is generic — it doesn't know about specific agents. Custom agents created via UI are persisted to DB and loaded on startup.

**Tech Stack:** Pydantic v2, SQLAlchemy async, FastAPI, existing pipeline

---

## Task 1: Create AgentDefinition Model

**Files:**
- Create: `backend/src/codecouncil/agents/definition.py`

The single source of truth for everything about an agent:

```python
from pydantic import BaseModel, Field
from typing import Any

class AgentDefinition(BaseModel):
    """Complete agent definition — identity, config, persona, prompts, policies."""

    # Identity
    handle: str                          # "archaeologist"
    name: str                            # "The Archaeologist"
    abbr: str                            # "AR"
    role: str                            # "Historian · Evidence Collector"
    short_role: str                      # "Historian"
    color: str                           # "#d4a574"
    icon: str                            # "eye" (lucide icon name)
    description: str = ""                # Short description

    # LLM Config
    temperature: float = 0.3
    max_tokens: int = 4096
    provider: str = ""                   # override default provider
    model: str = ""                      # override default model

    # Behavior
    debate_role: str = "analyst"         # analyst | challenger | proposer | scribe
    vote_weight: float = 1.0
    can_vote: bool = True
    can_deadlock: bool = False
    can_propose: bool = False

    # Persona (the full system prompt)
    persona: str = ""

    # Phase-specific prompt templates
    # Use {{repo_context}}, {{findings}}, {{proposals}}, etc. as template variables
    prompts: dict[str, str] = Field(default_factory=dict)
    # Keys: "analyze", "debate_challenge", "debate_defend", "debate_evidence", "vote", "synthesize"

    # Focus areas for analysis
    focus_areas: list[str] = Field(default_factory=list)

    # Policies (rules the agent follows)
    policies: dict[str, str] = Field(default_factory=dict)
    # Keys: "voting", "deadlock", "neutrality", etc.

    # Extra config (agent-specific)
    extra: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    is_builtin: bool = True
    is_enabled: bool = True

    def build_system_prompt(self, memory_context: str = "") -> str:
        """Build the full system prompt from persona + policies + memory."""
        parts = [self.persona]
        if self.policies:
            parts.append("\n## Your Policies")
            for name, policy in self.policies.items():
                parts.append(f"\n### {name}\n{policy}")
        if memory_context:
            parts.append(f"\n## Your Memory (from past sessions)\n{memory_context}")
        return "\n".join(parts)

    def get_prompt(self, phase: str, **kwargs) -> str:
        """Get a phase-specific prompt with template variables filled."""
        template = self.prompts.get(phase, "")
        if not template:
            return ""
        for key, value in kwargs.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template
```

- [ ] Create the file
- [ ] Verify: `python -c "from codecouncil.agents.definition import AgentDefinition; print('OK')"`
- [ ] Commit

---

## Task 2: Create Built-in Agent Definitions

**Files:**
- Create: `backend/src/codecouncil/agents/definitions/` directory
- Create: `backend/src/codecouncil/agents/definitions/__init__.py`
- Create: `backend/src/codecouncil/agents/definitions/archaeologist.py`
- Create: `backend/src/codecouncil/agents/definitions/skeptic.py`
- Create: `backend/src/codecouncil/agents/definitions/visionary.py`
- Create: `backend/src/codecouncil/agents/definitions/scribe.py`

Each file defines a single `definition = AgentDefinition(...)` with the FULL persona and prompts copied from the current pipeline.py hardcoded strings.

Example for archaeologist:

```python
# agents/definitions/archaeologist.py
from codecouncil.agents.definition import AgentDefinition

definition = AgentDefinition(
    handle="archaeologist",
    name="The Archaeologist",
    abbr="AR",
    role="Historian · Evidence Collector",
    short_role="Historian",
    color="#d4a574",
    icon="eye",
    description="Digs through repo history — commit patterns, churn, bus factor, dead code, stale TODOs",

    temperature=0.3,
    max_tokens=4096,
    debate_role="analyst",
    can_vote=True,
    can_deadlock=False,
    can_propose=False,

    persona="""You are the Archaeologist — the council's forensic historian and evidence collector.

You are declarative, grim, and data-first. You speak in facts. You cite commits.
You do not recommend. You surface what the codebase has survived.
You vote based on historical precedent — if the codebase has tried something before
and failed, you will flag it.
When presenting findings, reference specific files, commit hashes, and numbers.
Never editorialize. Let the data speak.""",

    prompts={
        "analyze": """Analyze this repository and produce findings. Focus on:
{{focus_areas_text}}

Repository context:
{{repo_context}}

For each finding, use this format:
[FINDING:CRITICAL|HIGH|MEDIUM|INFO] <description>
Implication: <why this matters>

Be thorough. Reference specific files, line counts, commit patterns, and author data.
Do NOT recommend solutions — only surface evidence.""",

        "debate_evidence": """You are the Archaeologist. Round {{round_number}} of debate on {{repo_name}}.

Visionary's position:
{{visionary_text}}

Skeptic's challenges:
{{skeptic_text}}

Provide factual evidence from commit history and file patterns.
State which side the data supports for each proposal. Be neutral and data-driven.
Reference specific patterns you found in the repository.""",

        "vote": """Vote on this proposal for {{repo_name}}:

Title: {{proposal_title}}
Goal: {{proposal_goal}}
Effort: {{proposal_effort}}
Description: {{proposal_description}}

Context from debate:
{{debate_context}}

Vote YES, NO, or ABSTAIN based on historical precedent.
If the codebase history shows this type of change has failed before, vote NO.
Include your confidence (0.0-1.0) and a one-sentence rationale.
Format: [VOTE:YES|NO|ABSTAIN] Rationale. Confidence: 0.X""",
    },

    focus_areas=[
        "file churn rate and stability patterns",
        "bus factor and author concentration",
        "dead code and unused modules",
        "TODO/FIXME accumulation and age",
        "commit sentiment and patterns",
        "file age distribution",
        "rewrite frequency",
    ],

    policies={
        "voting": "Vote based on historical precedent. Oppose proposals that history shows have failed before in this codebase.",
        "evidence": "Always cite specific files, commits, and numbers. Never speculate.",
    },
)
```

Copy the EXACT prompts from the current pipeline.py for each agent. The Skeptic gets:
- `debate_challenge` prompt (challenging proposals)
- `can_deadlock=True`
- Policy for deadlock rules

The Visionary gets:
- `debate_propose` prompt (creating proposals)
- `debate_defend` prompt (responding to challenges)
- `can_propose=True`

The Scribe gets:
- `synthesize` prompt (RFC generation)
- `can_vote=False`
- Policy for neutrality

- [ ] Create all 4 definition files with full prompts from pipeline.py
- [ ] Create __init__.py
- [ ] Verify all import correctly
- [ ] Commit

---

## Task 3: Create Agent Registry (Auto-Discovery)

**Files:**
- Rewrite: `backend/src/codecouncil/agents/registry.py`

The registry:
1. Scans `agents/definitions/` folder for Python files with a `definition` attribute
2. Loads custom agents from DB on startup (PersonaRepository, entries with `agent:` prefix)
3. Provides lookup by handle
4. Serves metadata to API

```python
class AgentRegistry:
    _agents: dict[str, AgentDefinition] = {}

    def discover_builtin(self) -> None:
        """Scan agents/definitions/ for built-in agent definitions."""
        definitions_dir = Path(__file__).parent / "definitions"
        for py_file in definitions_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            module = importlib.import_module(f"codecouncil.agents.definitions.{py_file.stem}")
            if hasattr(module, "definition"):
                defn = module.definition
                self._agents[defn.handle] = defn

    async def load_custom_from_db(self, session_factory) -> None:
        """Load custom agents from DB (persisted via API)."""
        async with session_factory() as db:
            repo = PersonaRepository(db)
            personas = await repo.list_personas()
            for p in personas:
                if p.name.startswith("agent:"):
                    import json
                    data = json.loads(p.content)
                    defn = AgentDefinition(**data, is_builtin=False)
                    self._agents[defn.handle] = defn

    def get(self, handle: str) -> AgentDefinition | None
    def list_all(self) -> list[AgentDefinition]
    def list_voting(self) -> list[AgentDefinition]  # agents where can_vote=True
    def list_analysts(self) -> list[AgentDefinition]  # debate_role != "scribe"
    def get_proposer(self) -> AgentDefinition | None  # debate_role == "proposer"
    def get_scribe(self) -> AgentDefinition | None  # debate_role == "scribe"
    def register(self, defn: AgentDefinition) -> None
    def unregister(self, handle: str) -> None
```

- [ ] Implement registry with auto-discovery
- [ ] Test: discover built-in agents, verify all 4 load
- [ ] Commit

---

## Task 4: Rewrite Pipeline to Use Agent Definitions

**Files:**
- Rewrite: `backend/src/codecouncil/api/pipeline.py`

This is the biggest change. The pipeline currently has ~1000 lines with hardcoded prompts. Replace with a generic agent runner that reads from definitions.

Key changes:

```python
async def run_real_council(run: dict, runs_store: dict, session_factory=None, agent_registry=None):
    # Get agents from registry
    analysts = agent_registry.list_analysts()
    proposer = agent_registry.get_proposer()
    scribe = agent_registry.get_scribe()
    voters = agent_registry.list_voting()

    # ANALYSIS PHASE
    for agent_def in analysts:
        prompt = agent_def.build_system_prompt(memory_context="")
        prompt += "\n\n" + agent_def.get_prompt("analyze",
            repo_context=full_context,
            focus_areas_text="\n".join(f"- {fa}" for fa in agent_def.focus_areas),
        )
        text, tokens_in, tokens_out = await llm_call(
            prompt, MODEL_HEAVY, agent_def.max_tokens, agent_def.temperature
        )
        # ... parse findings, emit events ...

    # DEBATE PHASE
    for round_num in range(1, max_rounds + 1):
        # Proposer proposes (round 1) or defends (round 2+)
        prompt = proposer.get_prompt("debate_propose" if round_num == 1 else "debate_defend", ...)

        # Each non-proposer agent responds
        for agent_def in analysts:
            if agent_def.handle == proposer.handle:
                continue
            phase_key = "debate_challenge" if agent_def.debate_role == "challenger" else "debate_evidence"
            prompt = agent_def.get_prompt(phase_key, ...)

    # VOTING PHASE
    for proposal in proposals:
        for agent_def in voters:
            prompt = agent_def.get_prompt("vote", ...)

    # SCRIBING PHASE
    prompt = scribe.get_prompt("synthesize", ...)
```

The pipeline becomes ~400 lines of GENERIC orchestration code that doesn't know about specific agents.

- [ ] Rewrite pipeline to use registry + definitions
- [ ] Test: run against a real repo, verify same quality output
- [ ] Commit

---

## Task 5: Wire Registry into App Lifecycle

**Files:**
- Modify: `backend/src/codecouncil/api/app.py`
- Modify: `backend/src/codecouncil/api/routes/runs.py`
- Modify: `backend/src/codecouncil/api/routes/agents.py`

App lifespan:
```python
# Create and populate agent registry
from codecouncil.agents.registry import AgentRegistry
registry = AgentRegistry()
registry.discover_builtin()
if session_factory:
    await registry.load_custom_from_db(session_factory)
app.state.agent_registry = registry
```

Startup interrupted-run detection:
```python
# Mark any "running" runs as "interrupted"
if session_factory:
    async with session_factory() as db:
        from sqlalchemy import text
        await db.execute(text("UPDATE runs SET status='interrupted', phase='error' WHERE status='running'"))
        await db.commit()
```

Pass registry to pipeline:
```python
asyncio.create_task(run_real_council(
    run, _runs,
    session_factory=session_factory,
    agent_registry=request.app.state.agent_registry,
))
```

Update agents API to serve from registry:
```python
@router.get("/agents")
async def list_agents(request: Request):
    registry = request.app.state.agent_registry
    return {"agents": [
        defn.model_dump(exclude={"persona", "prompts", "policies"})
        for defn in registry.list_all()
    ]}
```

- [ ] Wire registry into app lifespan
- [ ] Add interrupted-run detection on startup
- [ ] Pass registry to pipeline
- [ ] Update agents API
- [ ] Commit

---

## Task 6: Update Frontend to Fetch Agent Metadata from API

**Files:**
- Modify: `frontend/src/lib/constants.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: components that use agent constants

Make `constants.ts` a fallback cache. Components that need agent data should prefer API data when available.

The simplest approach: keep `constants.ts` as the static fallback (for SSR/initial render), but the config page and sessions page fetch from `/api/agents` for the latest list (including custom agents).

- [ ] Update constants.ts to be a fallback
- [ ] Verify custom agents from API appear in UI
- [ ] Commit

---

## Task 7: Delete Dead Code

**Files to delete or clean:**
- Delete: `backend/src/codecouncil/agents/archaeologist.py`
- Delete: `backend/src/codecouncil/agents/skeptic.py`
- Delete: `backend/src/codecouncil/agents/visionary.py`
- Delete: `backend/src/codecouncil/agents/scribe.py`
- Delete: `backend/src/codecouncil/config/defaults.py` (persona strings)
- Clean: `backend/src/codecouncil/config/schema.py` — remove per-agent config subclasses
- Clean: `backend/src/codecouncil/agents/base.py` — simplify or keep as interface

Update all imports and tests.

- [ ] Delete old agent class files
- [ ] Clean schema.py
- [ ] Clean defaults.py
- [ ] Update imports
- [ ] Fix tests
- [ ] Verify: all 157 tests pass (some may need updating)
- [ ] Commit

---

## Task 8: Full Statelessness Verification

- [ ] Start server, create a run, let it complete
- [ ] Kill server (Ctrl+C)
- [ ] Restart server
- [ ] Verify: completed run visible with all data
- [ ] Verify: custom agents (if any) still present
- [ ] Verify: any run that was "running" is now marked "interrupted"
- [ ] Verify: config changes survive restart
- [ ] Create a new run after restart — verify it works
- [ ] Commit any fixes
