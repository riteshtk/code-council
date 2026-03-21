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


def test_vote_confidence_range():
    with pytest.raises(Exception):
        Vote(
            run_id=uuid4(),
            proposal_id=uuid4(),
            agent="skeptic",
            vote=VoteType.NO,
            confidence=1.5,
        )


def test_council_state_creation():
    state: CouncilState = {
        "run_id": str(uuid4()),
        "repo_url": "https://github.com/test/repo",
        "config": {},
        "phase": Phase.INGESTING,
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
    assert state["findings"] == []
    assert state["phase"] == Phase.INGESTING


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


def test_all_event_types_exist():
    assert len(EventType) >= 30


def test_all_phases_exist():
    assert len(Phase) == 8
