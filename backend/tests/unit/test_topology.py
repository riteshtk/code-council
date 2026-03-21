"""Unit tests for debate topologies."""

import pytest
from codecouncil.debate.base import AgentTurn
from codecouncil.debate.registry import TopologyRegistry
from codecouncil.debate.adversarial import AdversarialTopology
from codecouncil.debate.collaborative import CollaborativeTopology
from codecouncil.debate.socratic import SocraticTopology
from codecouncil.debate.open_floor import OpenFloorTopology
from codecouncil.debate.panel import PanelTopology
from codecouncil.debate.custom import CustomTopology

AGENTS = ["archaeologist", "skeptic", "visionary", "scribe"]


def _make_state(**overrides):
    from uuid import uuid4

    base = {
        "run_id": str(uuid4()),
        "repo_url": "",
        "config": {},
        "phase": "debating",
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
    base.update(overrides)
    return base


def test_registry_has_all_topologies():
    names = TopologyRegistry.list_all()
    assert "adversarial" in names
    assert "collaborative" in names
    assert "socratic" in names
    assert "open_floor" in names
    assert "panel" in names
    assert "custom" in names


def test_registry_get():
    topo = TopologyRegistry.get("adversarial")
    assert isinstance(topo, AdversarialTopology)


def test_adversarial_turn_order():
    topo = AdversarialTopology()
    state = _make_state()
    turns = topo.get_turn_order(state, AGENTS)
    # First: visionary presents, then skeptic challenges
    assert turns[0].agent_handle == "visionary"
    assert turns[0].action == "propose"
    assert turns[1].agent_handle == "skeptic"
    assert turns[1].action == "challenge"


def test_adversarial_skeptic_can_interrupt():
    topo = AdversarialTopology()
    assert topo.can_interrupt("skeptic", "visionary") is True  # Deadlock
    assert topo.can_interrupt("archaeologist", "visionary") is False


def test_adversarial_should_end_round():
    topo = AdversarialTopology()
    state = _make_state()
    assert topo.should_end_round(state, 3, 3) is True  # Max rounds
    assert topo.should_end_round(state, 1, 3) is False


def test_collaborative_no_interrupts():
    topo = CollaborativeTopology()
    assert topo.can_interrupt("skeptic", "visionary") is False
    assert topo.can_interrupt("archaeologist", "skeptic") is False


def test_collaborative_turn_order():
    topo = CollaborativeTopology()
    state = _make_state()
    turns = topo.get_turn_order(state, AGENTS)
    handles = [t.agent_handle for t in turns]
    assert handles[0] == "archaeologist"
    assert handles[1] == "visionary"
    assert handles[2] == "skeptic"


def test_panel_fixed_rotation():
    topo = PanelTopology()
    state = _make_state()
    turns = topo.get_turn_order(state, AGENTS)
    handles = [t.agent_handle for t in turns]
    assert handles == ["archaeologist", "skeptic", "visionary", "scribe"]


def test_panel_no_interrupts():
    topo = PanelTopology()
    assert topo.can_interrupt("skeptic", "archaeologist") is False


def test_open_floor_all_can_interrupt():
    topo = OpenFloorTopology()
    assert topo.can_interrupt("archaeologist", "visionary") is True
    assert topo.can_interrupt("skeptic", "archaeologist") is True


def test_socratic_no_interrupts():
    topo = SocraticTopology()
    assert topo.can_interrupt("skeptic", "visionary") is False


def test_custom_topology_from_steps():
    steps = [
        {"agent": "archaeologist", "action": "present"},
        {"agent": "visionary", "action": "propose"},
        {"agent": "skeptic", "action": "challenge", "target": "visionary"},
    ]
    topo = CustomTopology(steps=steps)
    state = _make_state()
    turns = topo.get_turn_order(state, AGENTS)
    assert len(turns) == 3
    assert turns[0].agent_handle == "archaeologist"
    assert turns[2].target_agent == "visionary"


def test_custom_empty_steps():
    topo = CustomTopology(steps=[])
    state = _make_state()
    turns = topo.get_turn_order(state, AGENTS)
    assert turns == []
