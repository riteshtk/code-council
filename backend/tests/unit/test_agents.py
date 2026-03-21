"""Unit tests for CodeCouncil agent system."""

import pytest
from uuid import uuid4

from codecouncil.agents.base import BaseAgent, DebateContext, AgentResponse
from codecouncil.agents.definition import AgentDefinition
from codecouncil.agents.registry import AgentRegistry
from codecouncil.agents.archaeologist import Archaeologist
from codecouncil.agents.skeptic import Skeptic
from codecouncil.agents.visionary import Visionary
from codecouncil.agents.scribe import Scribe
from codecouncil.agents.memory import AgentMemoryManager
from codecouncil.models.agents import DebateRole, AgentMemory
from codecouncil.models.findings import Finding, Severity
from codecouncil.models.votes import VoteType
from codecouncil.providers.base import ProviderPlugin, Message, LLMConfig, LLMResponse


class MockProvider(ProviderPlugin):
    name = "mock"

    def __init__(self, response_text="mock response"):
        self.response_text = response_text

    async def stream(self, messages, config):
        for word in self.response_text.split():
            yield word

    async def complete(self, messages, config):
        return LLMResponse(content=self.response_text, input_tokens=10, output_tokens=5)

    def count_tokens(self, text):
        return len(text.split())

    def supports_streaming(self):
        return True

    def max_context_tokens(self):
        return 4096


def _make_defn(handle, debate_role="analyst", can_vote=True):
    """Helper to create a minimal AgentDefinition for testing."""
    return AgentDefinition(
        handle=handle, name=handle.capitalize(), abbr=handle[:3].upper(),
        role="test", short_role="test", color="#000", icon="test",
        debate_role=debate_role, can_vote=can_vote,
    )


def test_registry_register_and_get():
    registry = AgentRegistry()
    defn = _make_defn("archaeologist")
    registry.register(defn)
    assert registry.get("archaeologist") is defn


def test_registry_list_all():
    registry = AgentRegistry()
    registry.register(_make_defn("archaeologist"))
    registry.register(_make_defn("skeptic"))
    assert len(registry.list_all()) == 2


def test_agent_identities():
    assert Archaeologist().identity.handle == "archaeologist"
    assert Archaeologist().identity.color == "#d4a574"
    assert Archaeologist().identity.debate_role == DebateRole.ANALYST
    assert Skeptic().identity.handle == "skeptic"
    assert Skeptic().identity.color == "#ff6b6b"
    assert Skeptic().identity.debate_role == DebateRole.CHALLENGER
    assert Visionary().identity.handle == "visionary"
    assert Visionary().identity.color == "#6c5ce7"
    assert Visionary().identity.debate_role == DebateRole.PROPOSER
    assert Scribe().identity.handle == "scribe"
    assert Scribe().identity.color == "#4ecdc4"
    assert Scribe().identity.debate_role == DebateRole.SCRIBE


def test_parse_findings():
    text = """[FINDING:CRITICAL] Bus factor of 1 in core modules. Implication: Single point of failure.
[FINDING:HIGH] 43 unresolved TODOs aged 2+ years. Implication: Accumulated tech debt."""
    run_id = uuid4()
    findings = BaseAgent.parse_findings(text, "archaeologist", run_id)
    assert len(findings) == 2
    assert findings[0].severity == Severity.CRITICAL
    assert "Bus factor" in findings[0].content
    assert "Single point" in findings[0].implication
    assert findings[1].severity == Severity.HIGH


def test_parse_proposals():
    text = """[PROPOSAL]
Title: Extract DI module
Goal: Reduce coupling
Effort: L
"""
    run_id = uuid4()
    proposals = BaseAgent.parse_proposals(text, "visionary", run_id)
    assert len(proposals) == 1
    assert proposals[0].title == "Extract DI module"
    assert proposals[0].effort == "L"


def test_parse_vote_yes():
    text = "[VOTE:YES] The proposal is sound. Confidence: 0.8"
    vote = BaseAgent.parse_vote(text, "archaeologist", uuid4(), uuid4())
    assert vote.vote == VoteType.YES
    assert vote.confidence == 0.8


def test_parse_vote_no():
    text = "[VOTE:NO] Migration cost too high. Confidence: 0.9"
    vote = BaseAgent.parse_vote(text, "skeptic", uuid4(), uuid4())
    assert vote.vote == VoteType.NO
    assert vote.confidence == 0.9


def test_voting_agents_exclude_scribe():
    registry = AgentRegistry()
    registry.register(_make_defn("archaeologist", "analyst", can_vote=True))
    registry.register(_make_defn("skeptic", "challenger", can_vote=True))
    registry.register(_make_defn("visionary", "proposer", can_vote=True))
    registry.register(_make_defn("scribe", "scribe", can_vote=False))
    voting = registry.list_voting()
    handles = [a.handle for a in voting]
    assert "scribe" not in handles
    assert len(handles) == 3


def test_analyst_agents_exclude_scribe():
    registry = AgentRegistry()
    registry.register(_make_defn("archaeologist", "analyst"))
    registry.register(_make_defn("skeptic", "challenger"))
    registry.register(_make_defn("visionary", "proposer"))
    registry.register(_make_defn("scribe", "scribe"))
    analysts = registry.list_analysts()
    handles = [a.handle for a in analysts]
    assert "scribe" not in handles


@pytest.mark.asyncio
async def test_archaeologist_analyze_with_mock():
    provider = MockProvider("[FINDING:HIGH] High churn in core modules. Implication: Instability risk.")
    agent = Archaeologist(provider=provider)
    state = {
        "run_id": str(uuid4()),
        "repo_url": "https://github.com/test/repo",
        "config": {},
        "phase": "analysing",
        "repo_context": {"file_tree": [], "summary_stats": {"total_files": 10}},
        "findings": [], "proposals": [], "votes": [],
        "debate_rounds": [], "opening_statements": [],
        "rfc_content": "", "agent_memories": {},
        "events": [], "cost_total": 0.0,
        "human_review_pending": False, "cancelled": False,
    }
    findings = await agent.analyze(state)
    assert len(findings) >= 1
    assert findings[0].severity == Severity.HIGH


def test_persona_prompts():
    assert "evidence" in Archaeologist()._get_persona().lower() or "historian" in Archaeologist()._get_persona().lower()
    assert "risk" in Skeptic()._get_persona().lower() or "challenge" in Skeptic()._get_persona().lower()
    assert "proposal" in Visionary()._get_persona().lower() or "constructive" in Visionary()._get_persona().lower()
    assert "neutral" in Scribe()._get_persona().lower() or "secretary" in Scribe()._get_persona().lower()


@pytest.mark.asyncio
async def test_scribe_analyze_returns_empty():
    scribe = Scribe()
    state = {
        "run_id": str(uuid4()),
        "repo_url": "https://github.com/test/repo",
        "config": {},
        "phase": "analysing",
        "repo_context": {},
        "findings": [], "proposals": [], "votes": [],
        "debate_rounds": [], "opening_statements": [],
        "rfc_content": "", "agent_memories": {},
        "events": [], "cost_total": 0.0,
        "human_review_pending": False, "cancelled": False,
    }
    findings = await scribe.analyze(state)
    assert findings == []


@pytest.mark.asyncio
async def test_scribe_vote_always_abstains():
    scribe = Scribe()
    run_id = uuid4()
    proposal_id = uuid4()
    state = {
        "run_id": str(run_id),
        "repo_url": "https://github.com/test/repo",
        "config": {},
        "phase": "voting",
        "repo_context": {},
        "findings": [], "proposals": [], "votes": [],
        "debate_rounds": [], "opening_statements": [],
        "rfc_content": "", "agent_memories": {},
        "events": [], "cost_total": 0.0,
        "human_review_pending": False, "cancelled": False,
    }
    vote = await scribe.vote({"id": str(proposal_id), "title": "Test"}, state)
    assert vote.vote == VoteType.ABSTAIN
    assert vote.agent == "scribe"


@pytest.mark.asyncio
async def test_skeptic_declare_deadlock():
    skeptic = Skeptic()
    proposal = {"id": str(uuid4()), "title": "Dangerous refactor"}
    result = await skeptic.declare_deadlock(proposal, "Migration history shows 3 prior failures.")
    assert result["type"] == "DEADLOCK"
    assert result["agent"] == "skeptic"
    assert "failures" in result["evidence"]


def test_skeptic_can_deadlock_flag():
    assert Skeptic.can_deadlock is True


@pytest.mark.asyncio
async def test_memory_manager_load_empty():
    manager = AgentMemoryManager()
    memory = await manager.load_memory("archaeologist", session_factory=None)
    assert memory.agent_handle == "archaeologist"
    assert memory.session_summaries == []
    assert memory.known_patterns == []


@pytest.mark.asyncio
async def test_visionary_analyze_with_mock():
    provider = MockProvider("[FINDING:MEDIUM] Bounded context leakage in auth module. Implication: Coupling risk.")
    agent = Visionary(provider=provider)
    state = {
        "run_id": str(uuid4()),
        "repo_url": "https://github.com/test/repo",
        "config": {},
        "phase": "analysing",
        "repo_context": {"file_tree": [], "summary_stats": {"total_files": 5}},
        "findings": [], "proposals": [], "votes": [],
        "debate_rounds": [], "opening_statements": [],
        "rfc_content": "", "agent_memories": {},
        "events": [], "cost_total": 0.0,
        "human_review_pending": False, "cancelled": False,
    }
    findings = await agent.analyze(state)
    assert isinstance(findings, list)


def test_build_system_prompt_with_memory():
    agent = Archaeologist()
    agent.memory = AgentMemory(
        agent_handle="archaeologist",
        known_patterns=["High churn in auth module", "Bus factor 1 in payments"],
        interpersonal_history=["Skeptic challenged auth findings in session 3"],
    )
    prompt = agent._build_system_prompt()
    assert "High churn" in prompt
    assert "Skeptic challenged" in prompt
    assert "Memory" in prompt


def test_parse_vote_abstain_default():
    text = "No clear vote marker here."
    vote = BaseAgent.parse_vote(text, "archaeologist", uuid4(), uuid4())
    assert vote.vote == VoteType.ABSTAIN
    assert vote.confidence == 0.5
