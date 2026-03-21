"""Integration tests for the LangGraph council graph."""

import pytest
from uuid import uuid4
from codecouncil.graph.council_graph import build_council_graph
from codecouncil.graph.nodes import should_continue_debate, should_review


def test_graph_compiles():
    """Graph should compile without errors."""
    graph = build_council_graph()
    assert graph is not None


def test_should_continue_debate_max_rounds():
    state = {
        "config": {"council": {"max_rounds": 3}},
        "debate_rounds": [{"round": 1}, {"round": 2}, {"round": 3}],
        "proposals": [],
    }
    assert should_continue_debate(state) == "vote"


def test_should_continue_debate_unresolved():
    state = {
        "config": {"council": {"max_rounds": 3}},
        "debate_rounds": [{"round": 1}],
        "proposals": [{"status": "proposed", "title": "Test"}],
    }
    assert should_continue_debate(state) == "continue"


def test_should_continue_debate_all_resolved():
    state = {
        "config": {"council": {"max_rounds": 3}},
        "debate_rounds": [{"round": 1}],
        "proposals": [{"status": "passed"}, {"status": "failed"}],
    }
    assert should_continue_debate(state) == "vote"


def test_should_review_hitl_enabled():
    state = {"config": {"council": {"hitl_enabled": True}}}
    assert should_review(state) == "review"


def test_should_review_hitl_disabled():
    state = {"config": {"council": {"hitl_enabled": False}}}
    assert should_review(state) == "finalise"


def test_should_review_default():
    state = {"config": {}}
    assert should_review(state) == "finalise"


def test_graph_compiles_with_checkpointer():
    """Graph should compile with a MemorySaver checkpointer."""
    from codecouncil.graph.checkpointing import create_checkpointer
    checkpointer = create_checkpointer()
    graph = build_council_graph(checkpointer=checkpointer)
    assert graph is not None


def test_should_continue_debate_no_proposals():
    """With no proposals and rounds below max, should continue."""
    state = {
        "config": {"council": {"max_rounds": 3}},
        "debate_rounds": [{"round": 1}],
        "proposals": [],
    }
    # No unresolved proposals and below max rounds => vote (nothing to debate)
    assert should_continue_debate(state) == "vote"


def test_should_continue_debate_mixed_statuses():
    """With some resolved and some unresolved proposals below max rounds, should continue."""
    state = {
        "config": {"council": {"max_rounds": 3}},
        "debate_rounds": [{"round": 1}],
        "proposals": [
            {"status": "passed"},
            {"status": "challenged"},  # unresolved
        ],
    }
    assert should_continue_debate(state) == "continue"


def test_should_continue_debate_default_max_rounds():
    """Default max_rounds is 3."""
    state = {
        "config": {},
        "debate_rounds": [{"r": 1}, {"r": 2}, {"r": 3}],
        "proposals": [{"status": "proposed"}],
    }
    assert should_continue_debate(state) == "vote"
