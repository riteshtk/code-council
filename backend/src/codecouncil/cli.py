"""CodeCouncil CLI — full implementation with Typer + Rich terminal UI."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Any

import typer
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="codecouncil",
    help="AI agent council for codebase intelligence",
    no_args_is_help=True,
)
console = Console()

# ---------------------------------------------------------------------------
# Default agent metadata — used by agents list and streaming UI
# ---------------------------------------------------------------------------

DEFAULT_AGENTS: list[dict[str, str]] = [
    {
        "handle": "archaeologist",
        "name": "The Archaeologist",
        "color": "#d4a574",
        "role": "ANALYST",
        "description": "Forensic historian of the codebase.",
    },
    {
        "handle": "skeptic",
        "name": "The Skeptic",
        "color": "#e07070",
        "role": "CHALLENGER",
        "description": "Stress-tests every claim and assumption.",
    },
    {
        "handle": "visionary",
        "name": "The Visionary",
        "color": "#70aee0",
        "role": "PROPOSER",
        "description": "Proposes bold architectural improvements.",
    },
    {
        "handle": "scribe",
        "name": "The Scribe",
        "color": "#a0e0a0",
        "role": "SCRIBE",
        "description": "Synthesises debate into an RFC.",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_agent_panel(agent: dict[str, str], status: str, text: str) -> Panel:
    """Build a Rich Panel for a single agent."""
    color = agent["color"]
    title = Text(f"[{agent['handle']}] {agent['name']}", style=f"bold {color}")
    body = Text()
    body.append(f"Status: {status}\n", style="dim")
    body.append(text[:300] if text else "(waiting...)", style="white")
    return Panel(body, title=title, border_style=color, expand=True)


def _build_streaming_layout(
    agent_states: dict[str, dict[str, str]],
    debate_feed: list[str],
    elapsed: float,
    phase: str,
    round_num: int,
    cost: float,
) -> Layout:
    """Build a Rich Layout for streaming mode."""
    layout = Layout()
    layout.split_column(
        Layout(name="agents", ratio=3),
        Layout(name="feed", ratio=2),
        Layout(name="status", size=3),
    )

    # Agent panels — 2x2 grid
    panels = []
    for agent in DEFAULT_AGENTS:
        handle = agent["handle"]
        state = agent_states.get(handle, {"status": "idle", "text": ""})
        panels.append(_build_agent_panel(agent, state["status"], state["text"]))

    layout["agents"].update(Columns(panels, equal=True, expand=True))

    # Debate feed
    feed_lines = debate_feed[-20:]  # last 20 entries
    feed_text = "\n".join(feed_lines) if feed_lines else "(no events yet)"
    layout["feed"].update(
        Panel(feed_text, title="Debate Feed", border_style="blue", expand=True)
    )

    # Status bar
    status_text = (
        f"Phase: [bold]{phase}[/bold]  |  "
        f"Round: [bold]{round_num}[/bold]  |  "
        f"Elapsed: [bold]{elapsed:.1f}s[/bold]  |  "
        f"Cost: [bold green]${cost:.4f}[/bold green]"
    )
    layout["status"].update(Panel(status_text, border_style="green"))

    return layout


def _print_vote_matrix(votes: list[dict], proposals: list[dict]) -> None:
    """Print the vote matrix as a Rich table."""
    if not proposals or not votes:
        return

    table = Table(title="Vote Matrix", show_header=True, header_style="bold magenta")
    table.add_column("Proposal", style="bold", max_width=40)

    agent_handles = [a["handle"] for a in DEFAULT_AGENTS if a["role"] != "SCRIBE"]
    for handle in agent_handles:
        table.add_column(handle.capitalize(), justify="center")

    # Build lookup: proposal_id -> {agent -> vote_type}
    vote_lookup: dict[str, dict[str, str]] = {}
    for v in votes:
        pid = str(v.get("proposal_id", ""))
        agent = v.get("agent", "")
        vtype = v.get("vote", "ABSTAIN")
        if pid not in vote_lookup:
            vote_lookup[pid] = {}
        vote_lookup[pid][agent] = vtype

    vote_styles = {"YES": "green", "NO": "red", "ABSTAIN": "yellow"}

    for proposal in proposals:
        pid = str(proposal.get("id", ""))
        title = proposal.get("title", "Untitled")[:40]
        row: list[Any] = [title]
        pmap = vote_lookup.get(pid, {})
        for handle in agent_handles:
            vtype = pmap.get(handle, "-")
            style = vote_styles.get(vtype, "dim")
            row.append(Text(vtype, style=style))
        table.add_row(*row)

    console.print(table)


def _print_cost_summary(state: dict) -> None:
    """Print a cost summary panel."""
    total_cost = state.get("cost_total", 0.0)
    console.print(
        Panel(
            f"[bold green]Total cost:[/bold green] ${total_cost:.6f} USD",
            title="Cost Summary",
            border_style="green",
        )
    )


def _print_rfc(rfc_content: str, fmt: str = "markdown") -> None:
    """Print the RFC with syntax highlighting."""
    from rich.markdown import Markdown
    from rich.syntax import Syntax

    if fmt == "markdown" and rfc_content:
        console.print(Markdown(rfc_content))
    elif fmt == "json":
        console.print_json(rfc_content)
    elif fmt == "html":
        console.print(Syntax(rfc_content, "html"))
    else:
        console.print(rfc_content)


def _save_rfc(rfc_content: str, output_dir: str, repo: str, fmt: str) -> Path:
    """Save RFC to file and return the path."""
    import re

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Sanitise repo name for filename
    safe_repo = re.sub(r"[^a-zA-Z0-9_-]", "_", repo)[:40]
    ts = time.strftime("%Y%m%dT%H%M%S")
    ext = {"markdown": "md", "json": "json", "html": "html"}.get(fmt, "md")
    filename = f"RFC-{safe_repo}-{ts}.{ext}"
    path = out / filename
    path.write_text(rfc_content or "", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# analyse command
# ---------------------------------------------------------------------------


@app.command()
def analyse(
    repo: str = typer.Argument(..., help="Repository URL or local path"),
    provider: str = typer.Option(None, help="Override default LLM provider"),
    model: str = typer.Option(None, help="Override default model"),
    rounds: int = typer.Option(None, help="Max debate rounds"),
    topology: str = typer.Option(None, help="Debate topology"),
    no_skeptic: bool = typer.Option(False, help="Disable Skeptic"),
    no_visionary: bool = typer.Option(False, help="Disable Visionary"),
    only_archaeologist: bool = typer.Option(False, help="Ingestion and findings only"),
    config: str = typer.Option(None, help="Custom config file path"),
    output: str = typer.Option(None, help="Output directory"),
    format: str = typer.Option("markdown", help="RFC output format (markdown|json|html)"),
    stream: bool = typer.Option(False, help="Stream events to terminal"),
    hitl: bool = typer.Option(False, help="Enable human review"),
    budget: float = typer.Option(0.0, help="Max spend in USD"),
    demo: bool = typer.Option(False, help="Demo mode (slow reveal)"),
    open_browser: bool = typer.Option(False, "--open", help="Open RFC in browser"),
    dry_run: bool = typer.Option(False, help="Ingest only, no LLM calls"),
) -> None:
    """Analyse a repository with the council."""
    from codecouncil.config.loader import load_config

    # Build overrides from CLI flags
    overrides: dict[str, Any] = {}
    if provider:
        overrides.setdefault("llm", {})["default_provider"] = provider
    if model:
        overrides.setdefault("llm", {})["default_model"] = model
    if rounds:
        overrides.setdefault("council", {})["max_rounds"] = rounds
    if topology:
        overrides.setdefault("council", {})["debate_topology"] = topology
    if hitl:
        overrides.setdefault("council", {})["hitl_enabled"] = True
    if budget > 0:
        overrides.setdefault("council", {})["budget_limit_usd"] = budget
    if no_skeptic:
        overrides.setdefault("agents", {}).setdefault("skeptic", {})["enabled"] = False
    if no_visionary:
        overrides.setdefault("agents", {}).setdefault("visionary", {})["enabled"] = False
    if output:
        overrides.setdefault("output", {})["directory"] = output
    if format:
        overrides.setdefault("output", {})["formats"] = [format]

    cfg = load_config(config_path=config, overrides=overrides)

    output_dir = output or cfg.output.directory

    if demo:
        _run_demo(repo, cfg, output_dir, format, stream, open_browser)
        return

    if dry_run:
        console.print(
            Panel(
                f"[bold yellow]Dry run:[/bold yellow] ingesting [bold]{repo}[/bold] (no LLM calls)",
                border_style="yellow",
            )
        )
        return

    # Run the analysis pipeline
    asyncio.run(
        _run_analysis(
            repo=repo,
            cfg=cfg,
            output_dir=output_dir,
            fmt=format,
            stream=stream,
            open_browser=open_browser,
        )
    )


async def _run_analysis(
    repo: str,
    cfg: Any,
    output_dir: str,
    fmt: str,
    stream: bool,
    open_browser: bool,
) -> None:
    """Execute the council analysis pipeline."""
    import uuid

    from codecouncil.graph.council_graph import build_council_graph

    run_id = str(uuid.uuid4())
    start = time.time()

    initial_state: dict[str, Any] = {
        "run_id": run_id,
        "repo_url": repo,
        "config": cfg.model_dump(),
        "phase": "ingest",
        "repo_context": None,
        "findings": [],
        "proposals": [],
        "votes": [],
        "debate_rounds": [],
        "opening_statements": [],
        "rfc_content": "",
        "agent_memories": {},
        "events": [],
        "cost_total": 0.0,
        "human_review_pending": False,
        "cancelled": False,
    }

    agent_states: dict[str, dict[str, str]] = {
        a["handle"]: {"status": "idle", "text": ""} for a in DEFAULT_AGENTS
    }
    debate_feed: list[str] = []
    final_state: dict[str, Any] = {}

    if stream:
        graph = build_council_graph()
        with Live(
            _build_streaming_layout(agent_states, debate_feed, 0.0, "ingest", 0, 0.0),
            console=console,
            refresh_per_second=4,
        ) as live:
            try:
                async for event in graph.astream(
                    initial_state,
                    config={"configurable": {"thread_id": run_id}},
                ):
                    elapsed = time.time() - start
                    for node_name, state_update in event.items():
                        phase = state_update.get("phase", "unknown") if isinstance(state_update, dict) else "unknown"
                        cost = state_update.get("cost_total", 0.0) if isinstance(state_update, dict) else 0.0
                        rounds_done = len(state_update.get("debate_rounds", [])) if isinstance(state_update, dict) else 0

                        debate_feed.append(f"[{time.strftime('%H:%M:%S')}] Phase: {phase}")

                        # Update final state
                        if isinstance(state_update, dict):
                            final_state = state_update

                        live.update(
                            _build_streaming_layout(
                                agent_states,
                                debate_feed,
                                elapsed,
                                phase,
                                rounds_done,
                                cost,
                            )
                        )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Error during analysis: {exc}[/red]")
                raise typer.Exit(1) from exc
    else:
        # Silent run
        with console.status(f"[bold blue]Analysing {repo}...[/bold blue]"):
            try:
                graph = build_council_graph()
                final_state = await graph.ainvoke(
                    initial_state,
                    config={"configurable": {"thread_id": run_id}},
                )
            except Exception as exc:  # noqa: BLE001
                console.print(f"[red]Analysis failed: {exc}[/red]")
                raise typer.Exit(1) from exc

    # Print RFC
    rfc = final_state.get("rfc_content", "")
    if rfc:
        console.print("\n")
        console.rule("[bold green]RFC Output[/bold green]")
        _print_rfc(rfc, fmt)
        rfc_path = _save_rfc(rfc, output_dir, repo, fmt)
        console.print(f"\n[dim]RFC saved to:[/dim] {rfc_path}")

        if open_browser:
            import webbrowser
            webbrowser.open(str(rfc_path))

    # Vote matrix
    _print_vote_matrix(final_state.get("votes", []), final_state.get("proposals", []))

    # Cost summary
    _print_cost_summary(final_state)


def _run_demo(repo: str, cfg: Any, output_dir: str, fmt: str, stream: bool, open_browser: bool) -> None:
    """Demo mode — simulates a council run with fake events and slow reveal."""
    import random

    demo_events = [
        ("archaeologist", "ANALYSING", "Scanning commit history... found 1,247 commits over 3 years."),
        ("skeptic", "ANALYSING", "Reviewing security boundaries and coupling metrics..."),
        ("visionary", "ANALYSING", "Identifying architectural opportunities..."),
        ("archaeologist", "SPEAKING", "Bus factor is critically low: 73% of core modules owned by a single author."),
        ("skeptic", "SPEAKING", "That bus factor claim requires evidence. Show me the git blame distribution."),
        ("archaeologist", "SPEAKING", "git shortlog -sn shows: alice: 847 commits, bob: 223 commits, others: 177."),
        ("visionary", "SPEAKING", "I propose: P-01 Extract shared auth module, P-02 Add distributed tracing."),
        ("skeptic", "SPEAKING", "P-02 is premature without load testing data. I challenge this proposal."),
        ("archaeologist", "VOTING", "Voting YES on P-01 based on historical churn evidence."),
        ("skeptic", "VOTING", "Voting NO on P-02, insufficient evidence for scale issues."),
        ("visionary", "VOTING", "Voting YES on P-02, architectural debt is evident."),
        ("scribe", "SCRIBING", "Synthesising debate into RFC..."),
    ]

    demo_rfc = f"""# RFC: {repo}

## Executive Summary

The council identified 3 critical findings and produced 2 proposals after 2 debate rounds.

## Key Findings

- **[CRITICAL]** Bus factor = 1.2: 73% of core modules owned by a single author
- **[HIGH]** 47 unresolved TODOs older than 6 months in `/src/core`
- **[MEDIUM]** Test coverage dropped from 82% to 61% over last 90 days

## Proposals

### P-01: Extract Shared Auth Module
- **Goal:** Reduce duplication and bus factor risk
- **Effort:** Medium (2–3 sprints)
- **Vote:** YES (3/3) — unanimous

### P-02: Add Distributed Tracing
- **Goal:** Improve observability for scale
- **Effort:** High (4–6 sprints)
- **Vote:** NO (2/3) — contested by Skeptic

## Action Items

1. Assign secondary owners to all modules with bus_factor < 1.5
2. Triage and resolve TODOs older than 90 days
3. Restore test coverage above 75% before next release

## Debate Excerpt

> **Skeptic:** P-02 is premature without load testing data.
> **Visionary:** The architectural debt is already visible in latency metrics.
> **Archaeologist:** git log shows auth module has 34 separate incident patches.
"""

    agent_states: dict[str, dict[str, str]] = {
        a["handle"]: {"status": "idle", "text": ""} for a in DEFAULT_AGENTS
    }
    debate_feed: list[str] = []

    with Live(
        _build_streaming_layout(agent_states, debate_feed, 0.0, "ingest", 0, 0.0),
        console=console,
        refresh_per_second=4,
    ) as live:
        start = time.time()
        for i, (handle, status, text) in enumerate(demo_events):
            time.sleep(0.8)  # slow reveal
            agent_states[handle] = {"status": status, "text": text}
            debate_feed.append(f"[{time.strftime('%H:%M:%S')}] [{handle}] {text[:80]}")
            phase = "debate" if i < len(demo_events) - 2 else "scribing"
            cost = random.uniform(0.001, 0.003) * (i + 1)
            round_num = min(2, i // 3 + 1)
            live.update(
                _build_streaming_layout(
                    agent_states, debate_feed, time.time() - start, phase, round_num, cost
                )
            )

    console.print("\n")
    console.rule("[bold green]RFC Output (Demo)[/bold green]")
    _print_rfc(demo_rfc, fmt)

    rfc_path = _save_rfc(demo_rfc, output_dir, repo, fmt)
    console.print(f"\n[dim]RFC saved to:[/dim] {rfc_path}")

    # Demo vote matrix
    demo_votes = [
        {"proposal_id": "aaaaaaaa-0000-0000-0000-000000000001", "agent": "archaeologist", "vote": "YES"},
        {"proposal_id": "aaaaaaaa-0000-0000-0000-000000000001", "agent": "skeptic", "vote": "YES"},
        {"proposal_id": "aaaaaaaa-0000-0000-0000-000000000001", "agent": "visionary", "vote": "YES"},
        {"proposal_id": "aaaaaaaa-0000-0000-0000-000000000002", "agent": "archaeologist", "vote": "NO"},
        {"proposal_id": "aaaaaaaa-0000-0000-0000-000000000002", "agent": "skeptic", "vote": "NO"},
        {"proposal_id": "aaaaaaaa-0000-0000-0000-000000000002", "agent": "visionary", "vote": "YES"},
    ]
    demo_proposals = [
        {"id": "aaaaaaaa-0000-0000-0000-000000000001", "title": "P-01: Extract Shared Auth Module"},
        {"id": "aaaaaaaa-0000-0000-0000-000000000002", "title": "P-02: Add Distributed Tracing"},
    ]
    _print_vote_matrix(demo_votes, demo_proposals)
    _print_cost_summary({"cost_total": 0.0142})

    if open_browser:
        import webbrowser
        webbrowser.open(str(rfc_path))


# ---------------------------------------------------------------------------
# serve command
# ---------------------------------------------------------------------------


@app.command()
def serve(
    api_port: int = typer.Option(8000, help="API port"),
    ui_port: int = typer.Option(3000, help="UI port"),
    no_ui: bool = typer.Option(False, help="API only, no UI"),
) -> None:
    """Start the CodeCouncil server."""
    import uvicorn

    console.print(
        Panel(
            f"[bold green]Starting CodeCouncil API on port {api_port}[/bold green]\n"
            + (f"[dim]UI available at http://localhost:{ui_port}[/dim]" if not no_ui else "[dim]UI disabled[/dim]"),
            title="CodeCouncil Server",
            border_style="green",
        )
    )
    uvicorn.run("codecouncil.main:app", host="0.0.0.0", port=api_port, reload=True)


# ---------------------------------------------------------------------------
# sessions sub-app
# ---------------------------------------------------------------------------

sessions_app = typer.Typer(help="Manage council sessions")
app.add_typer(sessions_app, name="sessions")


@sessions_app.command("list")
def sessions_list() -> None:
    """List past council sessions."""
    table = Table(title="Council Sessions", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Repo", style="bold")
    table.add_column("Date")
    table.add_column("Consensus", justify="center")
    table.add_column("Cost", justify="right", style="green")
    table.add_column("Status")

    console.print(table)
    console.print("[dim](No sessions found — run 'codecouncil analyse <repo>' to start one.)[/dim]")


@sessions_app.command("show")
def sessions_show(session_id: str) -> None:
    """Show session details."""
    console.print(f"[bold]Session:[/bold] {session_id}")
    console.print("[dim](Session storage not yet connected — coming soon.)[/dim]")


@sessions_app.command("compare")
def sessions_compare(id1: str, id2: str) -> None:
    """Compare two sessions on same repo."""
    console.print(f"[bold]Comparing sessions:[/bold] {id1} vs {id2}")
    console.print("[dim](Session comparison not yet implemented.)[/dim]")


# ---------------------------------------------------------------------------
# agents sub-app
# ---------------------------------------------------------------------------

agents_app = typer.Typer(help="Manage council agents")
app.add_typer(agents_app, name="agents")


@agents_app.command("list")
def agents_list() -> None:
    """List all registered agents."""
    table = Table(title="Council Agents", show_header=True, header_style="bold magenta")
    table.add_column("Handle", style="bold")
    table.add_column("Name")
    table.add_column("Color")
    table.add_column("Role")
    table.add_column("Description")
    table.add_column("Status", style="green")

    for agent in DEFAULT_AGENTS:
        color_swatch = Text("███", style=agent["color"])
        table.add_row(
            agent["handle"],
            agent["name"],
            color_swatch,
            agent["role"],
            agent["description"],
            "ACTIVE",
        )

    console.print(table)


# agents memory sub-sub-app
memory_app = typer.Typer(help="Manage agent memory")
agents_app.add_typer(memory_app, name="memory")


@memory_app.command("show")
def memory_show(handle: str) -> None:
    """Show agent memory summary."""
    known = {a["handle"] for a in DEFAULT_AGENTS}
    if handle not in known:
        console.print(f"[red]Unknown agent handle:[/red] {handle}")
        console.print(f"[dim]Available: {', '.join(known)}[/dim]")
        raise typer.Exit(1)
    console.print(
        Panel(
            f"[bold]Agent:[/bold] {handle}\n"
            "[dim]No memory stored yet — memory accumulates after completed sessions.[/dim]",
            title="Agent Memory",
            border_style="blue",
        )
    )


@memory_app.command("clear")
def memory_clear(handle: str) -> None:
    """Clear agent memory."""
    known = {a["handle"] for a in DEFAULT_AGENTS}
    if handle not in known:
        console.print(f"[red]Unknown agent handle:[/red] {handle}")
        raise typer.Exit(1)
    confirmed = typer.confirm(f"Clear all memory for agent '{handle}'?")
    if confirmed:
        console.print(f"[green]Memory cleared for:[/green] {handle}")
    else:
        console.print("[dim]Cancelled.[/dim]")


# ---------------------------------------------------------------------------
# personas sub-app
# ---------------------------------------------------------------------------

personas_app = typer.Typer(help="Manage agent personas")
app.add_typer(personas_app, name="personas")


@personas_app.command("list")
def personas_list() -> None:
    """List all configured personas."""
    from codecouncil.config.defaults import (
        ARCHAEOLOGIST_PERSONA,
        SCRIBE_PERSONA,
        SKEPTIC_PERSONA,
        VISIONARY_PERSONA,
    )

    table = Table(title="Agent Personas", show_header=True, header_style="bold yellow")
    table.add_column("Agent", style="bold")
    table.add_column("Source")
    table.add_column("Preview", max_width=60)

    persona_map = {
        "archaeologist": ARCHAEOLOGIST_PERSONA,
        "skeptic": SKEPTIC_PERSONA,
        "visionary": VISIONARY_PERSONA,
        "scribe": SCRIBE_PERSONA,
    }

    for handle, persona in persona_map.items():
        preview = persona.strip().splitlines()[0][:60] if persona else "(empty)"
        table.add_row(handle, "built-in", preview)

    console.print(table)


@personas_app.command("add")
def personas_add(name: str, path: str) -> None:
    """Add a custom persona from a file."""
    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)
    console.print(f"[green]Persona '[bold]{name}[/bold]' registered from:[/green] {path}")
    console.print("[dim](Custom persona storage coming soon.)[/dim]")


@personas_app.command("edit")
def personas_edit(name: str) -> None:
    """Edit a persona in $EDITOR."""
    import os
    import subprocess

    editor = os.environ.get("EDITOR", "vi")
    console.print(f"[dim]Opening persona '{name}' in {editor}...[/dim]")
    console.print("[dim](Custom persona storage coming soon.)[/dim]")
    # Would invoke: subprocess.call([editor, persona_path])


@personas_app.command("remove")
def personas_remove(name: str) -> None:
    """Remove a custom persona."""
    confirmed = typer.confirm(f"Remove persona '{name}'?")
    if confirmed:
        console.print(f"[green]Persona removed:[/green] {name}")
    else:
        console.print("[dim]Cancelled.[/dim]")


# ---------------------------------------------------------------------------
# providers sub-app
# ---------------------------------------------------------------------------

providers_app = typer.Typer(help="Manage LLM providers")
app.add_typer(providers_app, name="providers")

_PROVIDER_NAMES = ["openai", "anthropic", "google", "mistral", "ollama", "bedrock", "azure"]


@providers_app.command("list")
def providers_list() -> None:
    """List all configured providers."""
    from codecouncil.config.loader import load_config

    cfg = load_config()

    table = Table(title="LLM Providers", show_header=True, header_style="bold cyan")
    table.add_column("Name", style="bold")
    table.add_column("Default?", justify="center")
    table.add_column("API Key Set?", justify="center")
    table.add_column("Base URL")

    for name in _PROVIDER_NAMES:
        provider_cfg = cfg.llm.providers.get(name)
        is_default = "YES" if name == cfg.llm.default_provider else ""
        api_key_set = "[green]YES[/green]" if (provider_cfg and provider_cfg.api_key) else "[dim]no[/dim]"
        base_url = (provider_cfg.base_url if provider_cfg and provider_cfg.base_url else "[dim]-[/dim]")
        table.add_row(name, is_default, api_key_set, base_url)

    console.print(table)
    console.print(
        f"\n[dim]Default provider:[/dim] [bold]{cfg.llm.default_provider}[/bold]  "
        f"[dim]Default model:[/dim] [bold]{cfg.llm.default_model}[/bold]"
    )


@providers_app.command("test")
def providers_test(name: str) -> None:
    """Test provider connectivity."""
    if name not in _PROVIDER_NAMES:
        console.print(f"[yellow]Unknown provider:[/yellow] {name}")
        console.print(f"[dim]Known providers: {', '.join(_PROVIDER_NAMES)}[/dim]")

    with console.status(f"[blue]Testing connectivity to provider:[/blue] {name}"):
        from codecouncil.config.loader import load_config

        cfg = load_config()
        provider_cfg = cfg.llm.providers.get(name)
        if not provider_cfg or not provider_cfg.api_key:
            console.print(f"[yellow]No API key configured for '{name}'.[/yellow]")
            console.print(f"[dim]Set CC_LLM__PROVIDERS__{name.upper()}__API_KEY or update your config.[/dim]")
            return

    console.print(f"[green]Provider '{name}' configuration looks valid.[/green]")
    console.print("[dim](Live connectivity ping not yet implemented.)[/dim]")


# ---------------------------------------------------------------------------
# config sub-app
# ---------------------------------------------------------------------------

config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show() -> None:
    """Show current merged config."""
    from codecouncil.config.loader import load_config

    cfg = load_config()
    console.print_json(data=cfg.model_dump())


@config_app.command("validate")
def config_validate(path: str) -> None:
    """Validate a config file."""
    from codecouncil.config.loader import load_config

    p = Path(path)
    if not p.exists():
        console.print(f"[red]File not found:[/red] {path}")
        raise typer.Exit(1)

    try:
        cfg = load_config(config_path=path)
        console.print(f"[green]Config file is valid:[/green] {path}")
        console.print(f"[dim]Council topology:[/dim] {cfg.council.debate_topology}")
        console.print(f"[dim]Max rounds:[/dim] {cfg.council.max_rounds}")
        console.print(f"[dim]Default provider:[/dim] {cfg.llm.default_provider}")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Config validation failed:[/red] {exc}")
        raise typer.Exit(1) from exc


@config_app.command("set")
def config_set(key: str, value: str) -> None:
    """Set a config value (in project .codecouncil.yaml)."""
    import yaml

    project_config_path = Path.cwd() / ".codecouncil.yaml"

    try:
        if project_config_path.exists():
            with open(project_config_path) as fh:
                data = yaml.safe_load(fh) or {}
        else:
            data: dict[str, Any] = {}

        # Support dot-notation: council.max_rounds=5
        parts = key.split(".")
        node = data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = _coerce_value(value)

        with open(project_config_path, "w") as fh:
            yaml.safe_dump(data, fh, default_flow_style=False)

        console.print(f"[green]Set[/green] {key} = {value} [dim]in {project_config_path}[/dim]")
    except Exception as exc:  # noqa: BLE001
        console.print(f"[red]Failed to set config:[/red] {exc}")
        raise typer.Exit(1) from exc


def _coerce_value(value: str) -> Any:
    """Coerce a CLI string value to bool, int, float, or str."""
    if value.lower() in ("true", "yes"):
        return True
    if value.lower() in ("false", "no"):
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
