"""All graph node functions for the CodeCouncil LangGraph council graph.

Each node is an async function that receives the full CouncilState dict and
returns a *partial* state update dict — LangGraph merges the returned dict
into the current state automatically.

Conditional edge functions (synchronous) are also defined here so they can
be imported together with the nodes.

Note on type annotations: LangGraph calls ``typing.get_type_hints()`` on
conditional-edge functions to infer schemas.  Using a forward-reference string
``"CouncilState"`` fails because CouncilState is not in the function's global
namespace.  We use plain ``dict`` annotations on all public node/edge callables
to avoid this and to satisfy LangGraph's schema inference.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: build a lightweight agent registry from state config
# ---------------------------------------------------------------------------

def _build_agent_registry(state: dict):
    """Build a default AgentRegistry with no providers (analysis-free mode).

    In a full run the registry would be built once at startup and injected via
    state or a closure.  The nodes retrieve it from state["config"] if a
    pre-built registry is attached (key: "_registry"), otherwise they
    construct a bare one with no LLM provider so the graph can at least run
    without crashing on missing config.
    """
    # Allow callers to inject a pre-built registry via private state key
    if "_registry" in state:
        return state["_registry"]

    from codecouncil.agents import (
        AgentRegistry,
        Archaeologist,
        Skeptic,
        Visionary,
        Scribe,
    )

    registry = AgentRegistry()
    registry.register("archaeologist", Archaeologist())
    registry.register("skeptic", Skeptic())
    registry.register("visionary", Visionary())
    registry.register("scribe", Scribe())
    return registry


# ---------------------------------------------------------------------------
# Node: ingest
# ---------------------------------------------------------------------------

async def ingest_node(state: dict) -> dict:
    """INGEST phase: Clone/fetch repo, run analyzers, build RepoContext.

    1. Extracts config from state.
    2. Calls ingestion.context.build_repo_context(repo_url, ingest_config).
    3. Returns repo_context (serialised to dict) and advances phase.

    Errors are caught and recorded in state so the graph can surface them
    without crashing the whole run.
    """
    from codecouncil.config.schema import IngestConfig

    repo_url: str = state.get("repo_url", "")
    config: dict = state.get("config", {})
    ingest_cfg_dict: dict = config.get("ingest", {})

    # Build a typed IngestConfig from the dict (with sane defaults)
    try:
        ingest_config = IngestConfig(**ingest_cfg_dict) if ingest_cfg_dict else IngestConfig()
    except Exception as exc:
        logger.warning("Could not parse IngestConfig: %s — using defaults", exc)
        ingest_config = IngestConfig()

    try:
        from codecouncil.ingestion.context import build_repo_context

        context = await build_repo_context(repo_url, ingest_config)
        return {
            "repo_context": context.model_dump(),
            "phase": "analysing",
        }
    except Exception as exc:
        logger.error("Ingestion failed for %s: %s", repo_url, exc)
        # Return a minimal stub so downstream nodes don't crash
        return {
            "repo_context": {
                "repo_url": repo_url,
                "repo_name": repo_url.rstrip("/").split("/")[-1],
                "error": str(exc),
            },
            "phase": "analysing",
        }


# ---------------------------------------------------------------------------
# Node: analyse
# ---------------------------------------------------------------------------

async def analyse_node(state: dict) -> dict:
    """ANALYSE phase: Fan-out all analyst agents in parallel.

    1. Retrieves analyst agents from the registry.
    2. Calls agent.analyze(state) for each agent concurrently.
    3. Returns a flat list of serialised Finding dicts.
    """
    registry = _build_agent_registry(state)
    analyst_agents = registry.get_analyst_agents()

    async def _run_agent(agent):
        try:
            findings = await agent.analyze(state)
            return [f.model_dump() for f in findings]
        except Exception as exc:
            logger.warning("Agent %s analyse failed: %s", agent.identity.handle, exc)
            return []

    results = await asyncio.gather(*[_run_agent(a) for a in analyst_agents])
    all_findings = [f for agent_findings in results for f in agent_findings]

    return {
        "findings": all_findings,
        "phase": "opening",
    }


# ---------------------------------------------------------------------------
# Node: opening
# ---------------------------------------------------------------------------

async def opening_node(state: dict) -> dict:
    """OPENING phase: Each agent presents its findings sequentially.

    Turn order: archaeologist → skeptic → visionary
    Each agent calls speak() with an empty DebateContext so they deliver
    their opening statement without prior debate history.
    """
    from codecouncil.agents.base import DebateContext

    registry = _build_agent_registry(state)
    ordered_handles = ["archaeologist", "skeptic", "visionary"]

    statements: list[dict] = []
    for handle in ordered_handles:
        try:
            agent = registry.get(handle)
        except KeyError:
            logger.warning("Agent %s not found in registry, skipping opening", handle)
            continue

        context = DebateContext(
            current_round=0,
            max_rounds=state.get("config", {}).get("council", {}).get("max_rounds", 3),
            debate_history=[],
        )
        try:
            response = await agent.speak(state, context)
            statements.append({
                "agent": handle,
                "content": response.content,
                "proposals": [p.model_dump() for p in response.proposals],
            })
        except Exception as exc:
            logger.warning("Agent %s opening speak failed: %s", handle, exc)
            statements.append({
                "agent": handle,
                "content": f"[Opening unavailable: {exc}]",
                "proposals": [],
            })

    return {
        "opening_statements": statements,
        "phase": "debating",
    }


# ---------------------------------------------------------------------------
# Node: debate
# ---------------------------------------------------------------------------

async def debate_node(state: dict) -> dict:
    """DEBATE phase: Structured multi-round debate per topology.

    1. Determines topology from config (default: adversarial).
    2. Computes the current round number from existing debate_rounds.
    3. Gets the turn order from the topology.
    4. Each agent speaks in turn; proposals are collected.
    5. Appends a new DebateRound record and returns updated state.
    """
    from codecouncil.agents.base import DebateContext
    from codecouncil.debate.registry import TopologyRegistry

    config: dict = state.get("config", {})
    council_cfg: dict = config.get("council", {})
    topology_name: str = council_cfg.get("debate_topology", "adversarial")
    max_rounds: int = council_cfg.get("max_rounds", 3)

    registry = _build_agent_registry(state)
    agent_handles = [h for h in ["archaeologist", "skeptic", "visionary"] if True]

    current_round_number = len(state.get("debate_rounds", [])) + 1

    try:
        topology = TopologyRegistry.get(topology_name)
    except KeyError:
        logger.warning("Unknown topology %r, falling back to adversarial", topology_name)
        topology = TopologyRegistry.get("adversarial")

    # Build list of agent handles that are registered
    registered_handles = list(registry.list_all().keys())
    # Exclude scribe from debate turns
    debate_handles = [h for h in registered_handles if h != "scribe"]

    turn_order = topology.get_turn_order(state, debate_handles)

    # Build a running debate history from previous rounds
    debate_history: list[dict] = []
    for prev_round in state.get("debate_rounds", []):
        for turn in prev_round.get("turns", []):
            debate_history.append(turn)

    turns: list[dict] = []
    proposals_this_round: list[dict] = []

    for agent_turn in turn_order:
        handle = agent_turn.agent_handle
        try:
            agent = registry.get(handle)
        except KeyError:
            logger.warning("Agent %s not in registry, skipping turn", handle)
            continue

        context = DebateContext(
            current_round=current_round_number,
            max_rounds=max_rounds,
            active_proposal=None,
            addressed_by=agent_turn.target_agent,
            debate_history=list(debate_history),
            addressing_agent=agent_turn.target_agent,
        )

        try:
            response = await agent.speak(state, context)
            turn_record = {
                "agent": handle,
                "action": agent_turn.action,
                "content": response.content,
                "round": current_round_number,
            }
            turns.append(turn_record)
            debate_history.append(turn_record)

            for proposal in response.proposals:
                proposals_this_round.append(proposal.model_dump())

        except Exception as exc:
            logger.warning("Agent %s debate speak failed: %s", handle, exc)
            turns.append({
                "agent": handle,
                "action": agent_turn.action,
                "content": f"[Turn unavailable: {exc}]",
                "round": current_round_number,
            })

    # Append this round's record
    new_round = {
        "round_number": current_round_number,
        "turns": turns,
    }
    updated_debate_rounds = list(state.get("debate_rounds", [])) + [new_round]

    # Accumulate proposals (avoid duplicates by title naively)
    existing_proposals = list(state.get("proposals", []))
    existing_titles = {p.get("title") for p in existing_proposals}
    for p in proposals_this_round:
        if p.get("title") not in existing_titles:
            existing_proposals.append(p)
            existing_titles.add(p.get("title"))

    return {
        "debate_rounds": updated_debate_rounds,
        "proposals": existing_proposals,
        "phase": "debating",
    }


# ---------------------------------------------------------------------------
# Node: voting
# ---------------------------------------------------------------------------

async def voting_node(state: dict) -> dict:
    """VOTING phase: Each voting agent votes on every unresolved proposal.

    1. Retrieves voting agents (excludes Scribe).
    2. For each unresolved proposal, collects votes from all voting agents.
    3. Determines outcome (PASSED / FAILED / DEADLOCKED) based on vote_threshold.
    4. Returns updated proposals list and flat votes list.
    """
    config: dict = state.get("config", {})
    council_cfg: dict = config.get("council", {})
    vote_threshold: float = council_cfg.get("vote_threshold", 0.5)

    registry = _build_agent_registry(state)
    voting_agents = registry.get_voting_agents()

    proposals: list[dict] = list(state.get("proposals", []))
    all_votes: list[dict] = list(state.get("votes", []))

    unresolved_statuses = {"proposed", "challenged", "revised", "PROPOSED", "CHALLENGED", "REVISED"}

    for i, proposal in enumerate(proposals):
        if proposal.get("status") not in unresolved_statuses:
            continue

        proposal_votes: list[dict] = []

        async def _cast_vote(agent, prop=proposal):
            try:
                vote = await agent.vote(prop, state)
                return vote.model_dump()
            except Exception as exc:
                logger.warning("Agent %s vote failed: %s", agent.identity.handle, exc)
                return None

        vote_results = await asyncio.gather(*[_cast_vote(a) for a in voting_agents])
        for v in vote_results:
            if v is not None:
                proposal_votes.append(v)
                all_votes.append(v)

        # Tally
        yes_votes = sum(1 for v in proposal_votes if v.get("vote") in ("YES", "yes"))
        no_votes = sum(1 for v in proposal_votes if v.get("vote") in ("NO", "no"))
        total_votes = len(proposal_votes)

        if total_votes == 0:
            proposals[i] = {**proposal, "status": "DEADLOCKED"}
        else:
            yes_ratio = yes_votes / total_votes
            no_ratio = no_votes / total_votes
            if yes_ratio > vote_threshold:
                proposals[i] = {**proposal, "status": "PASSED"}
            elif no_ratio > vote_threshold:
                proposals[i] = {**proposal, "status": "FAILED"}
            else:
                proposals[i] = {**proposal, "status": "DEADLOCKED"}

    return {
        "votes": all_votes,
        "proposals": proposals,
        "phase": "scribing",
    }


# ---------------------------------------------------------------------------
# Node: scribing
# ---------------------------------------------------------------------------

async def scribing_node(state: dict) -> dict:
    """SCRIBING phase: Scribe agent synthesizes the RFC document.

    1. Retrieves the Scribe agent from the registry.
    2. Calls scribe.synthesize_rfc(state) to produce the full RFC text.
    3. Returns the RFC content string.
    """
    registry = _build_agent_registry(state)

    try:
        scribe = registry.get("scribe")
        rfc_content = await scribe.synthesize_rfc(state)
    except Exception as exc:
        logger.error("Scribing failed: %s", exc)
        rfc_content = f"[RFC synthesis unavailable: {exc}]"

    return {
        "rfc_content": rfc_content,
        "phase": "review",
    }


# ---------------------------------------------------------------------------
# Node: review
# ---------------------------------------------------------------------------

async def review_node(state: dict) -> dict:
    """REVIEW phase: Human-in-the-loop review step.

    If HITL is not enabled, this node is a pass-through.
    When HITL is enabled, it signals the graph to pause by setting
    human_review_pending = True.  The calling code (API / CLI) is responsible
    for resuming the graph with updated state after human input is received.

    In a full LangGraph HITL setup, an interrupt() call would be placed here;
    for now the pending flag serves as the hook.
    """
    config: dict = state.get("config", {})
    hitl_enabled: bool = config.get("council", {}).get("hitl_enabled", False)

    if not hitl_enabled:
        return {"human_review_pending": False, "phase": "finalise"}

    # Signal that we are waiting for human input
    return {"human_review_pending": True, "phase": "review"}


# ---------------------------------------------------------------------------
# Node: finalise
# ---------------------------------------------------------------------------

async def finalise_node(state: dict) -> dict:
    """FINALISE phase: Compute consensus score, update agent memories, close run.

    1. Calculates consensus score = passed_proposals / total_proposals.
    2. Updates agent memories via memory manager (best-effort; DB may not be up).
    3. Returns final phase = "done".
    """
    proposals: list[dict] = state.get("proposals", [])
    total = len(proposals)
    passed = sum(1 for p in proposals if p.get("status") in ("passed", "PASSED"))
    consensus_score = (passed / total) if total > 0 else 0.0

    # Best-effort memory update — skip if providers are not configured
    registry = _build_agent_registry(state)
    memory_manager_cls = None
    try:
        from codecouncil.agents.memory import AgentMemoryManager
        memory_manager_cls = AgentMemoryManager
    except Exception:
        pass

    if memory_manager_cls is not None:
        mm = memory_manager_cls()
        for handle, agent in registry.list_all().items():
            try:
                await agent.update_memory(state)
            except Exception as exc:
                logger.debug("Memory update skipped for %s: %s", handle, exc)

    # Accumulate cost (if tracked by providers in state events)
    events: list[dict] = state.get("events", [])
    cost_from_events = sum(e.get("cost_usd", 0.0) for e in events if isinstance(e, dict))
    cost_total = state.get("cost_total", 0.0) + cost_from_events

    return {
        "phase": "done",
        "cost_total": cost_total,
        "human_review_pending": False,
    }


# ---------------------------------------------------------------------------
# Conditional edge functions
# ---------------------------------------------------------------------------

def should_continue_debate(state: dict) -> str:
    """Decide whether to continue debating or move to voting.

    Returns "vote" if:
    - The maximum number of debate rounds has been reached, OR
    - There are no unresolved proposals left.

    Returns "continue" otherwise.
    """
    config = state.get("config", {})
    max_rounds: int = config.get("council", {}).get("max_rounds", 3)
    current_rounds: int = len(state.get("debate_rounds", []))

    proposals = state.get("proposals", [])
    unresolved_statuses = {"proposed", "challenged", "revised", "PROPOSED", "CHALLENGED", "REVISED"}
    unresolved = [p for p in proposals if p.get("status") in unresolved_statuses]

    if current_rounds >= max_rounds or not unresolved:
        return "vote"
    return "continue"


def should_review(state: dict) -> str:
    """Decide whether to enter HITL review or go directly to finalise.

    Returns "review" if hitl_enabled is True in config, otherwise "finalise".
    """
    config = state.get("config", {})
    hitl: bool = config.get("council", {}).get("hitl_enabled", False)
    if hitl:
        return "review"
    return "finalise"


def review_decision(state: dict) -> str:
    """After human review, decide next step.

    If human_review_pending is still True the review was not completed, go to
    finalise anyway to avoid loops.  A "redebate" key in state can signal that
    the human requested a re-debate round.
    """
    if state.get("redebate_requested"):
        return "redebate"
    return "finalise"
