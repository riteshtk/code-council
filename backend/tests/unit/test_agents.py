"""Unit tests for CodeCouncil agent system."""

import pytest
from uuid import uuid4

from codecouncil.agents.base import BaseAgent, DebateContext, AgentResponse
from codecouncil.agents.definition import AgentDefinition
from codecouncil.agents.registry import AgentRegistry
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


def test_registry_discover_builtin():
    """Registry discovers all 4 built-in agent definitions."""
    registry = AgentRegistry()
    registry.discover_builtin()
    handles = [a.handle for a in registry.list_all()]
    assert "archaeologist" in handles
    assert "skeptic" in handles
    assert "visionary" in handles
    assert "scribe" in handles


def test_builtin_agent_definitions():
    """Built-in definitions have correct debate roles and properties."""
    registry = AgentRegistry()
    registry.discover_builtin()

    arch = registry.get("archaeologist")
    assert arch is not None
    assert arch.debate_role == "analyst"
    assert arch.is_builtin is True

    skeptic = registry.get("skeptic")
    assert skeptic is not None
    assert skeptic.debate_role == "challenger"
    assert skeptic.can_deadlock is True

    visionary = registry.get("visionary")
    assert visionary is not None
    assert visionary.debate_role == "proposer"
    assert visionary.can_propose is True

    scribe = registry.get("scribe")
    assert scribe is not None
    assert scribe.debate_role == "scribe"
    assert scribe.can_vote is False


def test_definition_to_api_dict():
    defn = _make_defn("archaeologist")
    api = defn.to_api_dict()
    assert api["handle"] == "archaeologist"
    assert api["id"] == "archaeologist"
    assert "name" in api
    assert "color" in api
    assert "debate_role" in api


def test_definition_build_system_prompt():
    defn = _make_defn("archaeologist")
    defn.persona = "You are the Archaeologist."
    defn.policies = {"evidence": "Always cite commits."}
    prompt = defn.build_system_prompt(memory_context="High churn in auth module")
    assert "Archaeologist" in prompt
    assert "evidence" in prompt
    assert "High churn" in prompt


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


def test_registry_unregister_custom():
    registry = AgentRegistry()
    defn = _make_defn("custom-agent")
    defn.is_builtin = False
    registry.register(defn)
    assert registry.get("custom-agent") is not None
    assert registry.unregister("custom-agent") is True
    assert registry.get("custom-agent") is None


def test_registry_unregister_builtin_fails():
    registry = AgentRegistry()
    defn = _make_defn("archaeologist")
    defn.is_builtin = True
    registry.register(defn)
    assert registry.unregister("archaeologist") is False
    assert registry.get("archaeologist") is not None


@pytest.mark.asyncio
async def test_memory_manager_load_empty():
    manager = AgentMemoryManager()
    memory = await manager.load_memory("archaeologist", session_factory=None)
    assert memory.agent_handle == "archaeologist"
    assert memory.session_summaries == []
    assert memory.known_patterns == []


def test_parse_vote_abstain_default():
    text = "No clear vote marker here."
    vote = BaseAgent.parse_vote(text, "archaeologist", uuid4(), uuid4())
    assert vote.vote == VoteType.ABSTAIN
    assert vote.confidence == 0.5


def test_persona_prompts_in_definitions():
    """Built-in definitions have substantive persona text."""
    registry = AgentRegistry()
    registry.discover_builtin()
    for defn in registry.list_all():
        assert isinstance(defn.persona, str)
        assert len(defn.persona) > 50, f"{defn.handle} persona too short"
